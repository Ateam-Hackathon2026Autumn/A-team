#!/usr/bin/env python3
"""Terraform の出力から単発 Fargate タスクを実行し、DB 初期化の成否を返す。"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


INFRA_DIR = Path(__file__).resolve().parents[1]
INITIAL_DATA_COMMAND = [
    "sh", "-c",
    "python manage.py migrate --noinput && python manage.py loaddata prefectures categories",
]


class MigrationError(RuntimeError):
    """終了コードだけで成功と誤認しないための実行エラー。"""


def json_command(command, env, *, stdin_value=None, sensitive=False):
    # shell を使わず、Secret の値も引数や一時ファイルへ展開しない。
    result = subprocess.run(command, env=env, input=stdin_value, text=True, capture_output=True, check=False)
    if result.returncode:
        if sensitive:
            raise MigrationError("Secret の登録に失敗しました。認証先・権限・Secret の状態を確認してください。")
        raise MigrationError(f"{command[0]} の実行に失敗しました: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MigrationError(f"{command[0]} から JSON を取得できませんでした。") from exc


class AwsCli:
    def __init__(self, region, env):
        self.region = region
        self.env = env

    def __call__(self, service, operation, request):
        command = ["aws", "--region", self.region, "--output", "json", "--no-cli-pager"]
        if self.env.get("AWS_PROFILE"):
            command += ["--profile", self.env["AWS_PROFILE"]]
        payload = dict(request)
        sensitive = service == "secretsmanager" and operation == "put-secret-value"
        # JSON 全体を file:///dev/stdin で読む経路は、一部の AWS CLI v2 で失敗する。
        # 公開パラメータは JSON 引数、SecretString だけは専用パラメータの stdin に分ける。
        # 呼び出し元の request は変更せず、秘密値を引数・ディスク・エラーログへ出さない。
        secret_value = payload.pop("SecretString") if sensitive else None
        command += [service, operation, "--cli-input-json", json.dumps(payload)]
        if sensitive:
            command += ["--secret-string", "file:///dev/stdin"]
        return json_command(command, self.env, stdin_value=secret_value, sensitive=sensitive)


def build_request(config, load_initial_data=False):
    request = {
        "cluster": config["cluster"],
        # family:latest ではなく、apply 済みのリビジョン ARN に固定する。
        "taskDefinition": config["task_definition"],
        "launchType": "FARGATE",
        "platformVersion": "1.4.0",
        "count": 1,
        "networkConfiguration": config["network_configuration"],
        "clientToken": uuid.uuid4().hex,
        "startedBy": f"db-migration-{uuid.uuid4().hex[:16]}",
    }
    if load_initial_data:
        request["overrides"] = {"containerOverrides": [{
            "name": config["container_name"],
            "command": INITIAL_DATA_COMMAND,
        }]}
    return request


def check_account(config, aws):
    identity = aws("sts", "get-caller-identity", {})
    if identity.get("Account") != config["aws_account_id"]:
        raise MigrationError("AWS の認証先が Terraform の対象アカウントと一致しません。")


def preflight(config, aws, *, require_idle_service=True):
    check_account(config, aws)
    if not require_idle_service:
        # apply 中はサービスをまだ作っていない場合がある。resource 参照の循環も避ける。
        return
    response = aws("ecs", "describe-services", {
        "cluster": config["cluster"], "services": [config["service"]],
    })
    services = response.get("services", [])
    if response.get("failures") or len(services) != 1:
        raise MigrationError("対象サービスを確認できません。先に基盤の apply を完了してください。")
    service = services[0]
    if service.get("status") != "ACTIVE" or any(
        service.get(key) != 0 for key in ("desiredCount", "runningCount", "pendingCount")
    ):
        raise MigrationError(
            "この初期デプロイ手順ではサービスの停止が必要です。"
            "desired_count = 0 で apply し、実行中・起動待ちタスクが0になってから実行してください。"
        )


def wait_for_completion(config, aws, task_arn, timeout, poll_interval=5):
    deadline = time.monotonic() + timeout
    last_status = None
    while time.monotonic() < deadline:
        response = aws("ecs", "describe-tasks", {
            "cluster": config["cluster"], "tasks": [task_arn],
        })
        # RunTask 直後の MISSING は ECS の結果整合性による場合がある。
        failures = response.get("failures", [])
        if any(failure.get("reason") != "MISSING" for failure in failures):
            raise MigrationError(f"タスクの状態取得に失敗しました: {failures}")
        tasks = response.get("tasks", [])
        task = next((task for task in tasks if task.get("taskArn") == task_arn), None)
        if task:
            status = task.get("lastStatus")
            if status != last_status:
                print(f"タスク状態: {status}", flush=True)
                last_status = status
            if status == "STOPPED":
                containers = [c for c in task.get("containers", []) if c.get("name") == config["container_name"]]
                if (len(containers) == 1 and containers[0].get("exitCode") == 0
                        and task.get("stopCode") == "EssentialContainerExited"):
                    return
                exits = [(c.get("name"), c.get("exitCode"), c.get("reason")) for c in containers]
                raise MigrationError(
                    f"migration が正常終了しませんでした。stopCode={task.get('stopCode')}, "
                    f"reason={task.get('stoppedReason')}, containers={exits}"
                )
        time.sleep(min(poll_interval, max(0, deadline - time.monotonic())))
    # MySQL の DDL を途中で中断しない。タスクは勝手に停止・再実行しない。
    raise MigrationError(
        "完了待ちがタイムアウトしました。タスクは継続している可能性があります。"
        "状態確認が終わるまで、再実行やサービス公開をしないでください。"
    )


def execute(config, aws, *, load_initial_data=False, timeout=900, require_idle_service=True):
    preflight(config, aws, require_idle_service=require_idle_service)
    # 前の apply が中断されても、動き続けている migration と並列実行しない。
    family = config["task_definition"].rsplit("/", 1)[-1].rsplit(":", 1)[0]
    active = aws("ecs", "list-tasks", {
        "cluster": config["cluster"], "family": family, "desiredStatus": "RUNNING",
    }).get("taskArns", [])
    if active:
        raise MigrationError(f"migration タスクが既に実行中です。状態を確認してから再実行してください: {active}")
    print(f"対象: {config['cluster']} / {config['task_definition']}", flush=True)
    print(f"イメージ: {config['image']}", flush=True)
    request = build_request(config, load_initial_data)
    print(f"実行ID（ECS startedBy）: {request['startedBy']}", flush=True)
    response = aws("ecs", "run-task", request)
    tasks = response.get("tasks", [])
    # RunTask は HTTP / CLI が成功していても failures を返すことがある。
    if response.get("failures") or len(tasks) != 1 or not tasks[0].get("taskArn"):
        raise MigrationError(
            f"単発タスクを起動できませんでした: {response.get('failures', [])}, "
            f"起動済みタスク={[task.get('taskArn') for task in tasks]}"
        )
    task_arn = tasks[0]["taskArn"]
    print(f"タスク ARN: {task_arn}", flush=True)
    print(
        f"CloudWatch Logs: {config['log_group']} / "
        f"{config['log_stream_prefix']}/{config['container_name']}/{task_arn.rsplit('/', 1)[-1]}",
        flush=True,
    )
    wait_for_completion(config, aws, task_arn, timeout)
    print("DB migration が正常終了しました（コンテナ終了コード0）。", flush=True)


def positive_seconds(value):
    value = int(value)
    if value <= 0:
        raise argparse.ArgumentTypeError("1秒以上を指定してください。")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", nargs="?", choices=["dev", "prod"])
    parser.add_argument("--from-terraform", action="store_true", help="apply 用: DEPLOY_CONFIG_JSON から設定を直接受け取る")
    parser.add_argument("--profile", help="Terraform backend と AWS CLI に使う AWS_PROFILE")
    parser.add_argument("--load-initial-data", action="store_true", help="初回のみ: migrate 成功後に prefectures・categories を投入")
    parser.add_argument("--timeout", type=positive_seconds, default=900, help="完了待ちの上限秒数（既定900）")
    args = parser.parse_args(argv)
    if args.from_terraform == bool(args.environment):
        parser.error("環境名、または --from-terraform のどちらか一方を指定してください。")
    env = {**os.environ, "AWS_PAGER": "", "AWS_CLI_AUTO_PROMPT": "off"}
    if args.profile:
        env["AWS_PROFILE"] = args.profile
        env["AWS_DEFAULT_PROFILE"] = args.profile
    try:
        if args.from_terraform:
            # apply が state をロックしている最中に Terraform CLI を再起動しない。
            config = json.loads(env["DEPLOY_CONFIG_JSON"])
        else:
            config = json_command([
                "terraform", f"-chdir={INFRA_DIR / 'environments' / args.environment}",
                "output", "-json", "ecs_migration",
            ], env)
        execute(config, AwsCli(config["aws_region"], env),
                load_initial_data=args.load_initial_data or config.get("load_initial_data", False),
                timeout=config.get("timeout_seconds", args.timeout) if args.from_terraform else args.timeout,
                require_idle_service=not args.from_terraform)
    except (MigrationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"失敗: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("待機を中断しました。起動済みタスクの状態を確認してから次へ進んでください。", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
