#!/usr/bin/env python3
"""apply から受け取る ARN に、未登録の場合だけ Django SECRET_KEY を保存する。"""

import json
import os
import secrets
import sys
import uuid

from run_migration import AwsCli, MigrationError, check_account


def ensure_secret(config, aws):
    check_account(config, aws)
    # 値の読み出し権限を必要とせず、バージョンのメタデータだけで確認する。
    metadata = aws("secretsmanager", "describe-secret", {"SecretId": config["secret_arn"]})
    if metadata.get("DeletedDate"):
        raise MigrationError("Django Secret が削除待機中です。復旧または削除完了を確認してください。")
    if any("AWSCURRENT" in stages for stages in metadata.get("VersionIdsToStages", {}).values()):
        print("Django Secret は登録済みです。既存の値を維持します。", flush=True)
        return
    value = secrets.token_urlsafe(64)
    aws("secretsmanager", "put-secret-value", {
        "SecretId": config["secret_arn"],
        "ClientRequestToken": uuid.uuid4().hex,
        "SecretString": value,
    })
    print("Django Secret の値を生成・登録しました。", flush=True)


def main():
    try:
        env = {**os.environ, "AWS_PAGER": "", "AWS_CLI_AUTO_PROMPT": "off"}
        config = json.loads(env["DEPLOY_CONFIG_JSON"])
        ensure_secret(config, AwsCli(config["aws_region"], env))
    except (MigrationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"失敗: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
