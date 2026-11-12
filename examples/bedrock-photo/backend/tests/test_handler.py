"""Bedrock の応答を Mock に置き換え、AWS へ通信せず認証・入出力を検証する。"""

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location("handler", Path(__file__).parents[1] / "handler.py")
handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler)


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.token = "test-only-fixture-password"
        self.auth_hash_patch = patch.object(handler, "API_TOKEN_SHA256", hashlib.sha256(self.token.encode()).hexdigest())
        self.auth_hash_patch.start()
        self.addCleanup(self.auth_hash_patch.stop)
        self.client = Mock()
        self.client.converse.return_value = {"output": {"message": {"content": [{"toolUse": {
            "name": "report_photo", "input": {"summary": "緑色の画像です。", "objects": [], "texts": [], "details": []}
        }}]}}}
        self.context = SimpleNamespace(aws_request_id="test-request")
        self.patch = patch.object(handler, "bedrock_client", return_value=self.client)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def event(self, image=None, **overrides):
        value = {"rawPath": "/api/analyze", "requestContext": {"http": {"method": "POST"}},
                 "headers": {"content-type": "application/json", "authorization": f"Bearer {self.token}"},
                 "body": json.dumps({"image": image or {"format": "jpeg", "base64": base64.b64encode(b"\xff\xd8\xfffixture").decode()}})}
        value.update(overrides)
        return value

    def test_image_bytes_and_structured_response(self):
        response = handler.lambda_handler(self.event(), self.context)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(json.loads(response["body"])["analysis"]["summary"], "緑色の画像です。")
        invocation = self.client.converse.call_args.kwargs
        self.assertEqual(invocation["messages"][0]["content"][0]["image"]["source"]["bytes"], b"\xff\xd8\xfffixture")
        self.assertNotIn("temperature", invocation["inferenceConfig"])
        self.assertEqual(invocation["additionalModelRequestFields"]["thinking"]["type"], "disabled")

    def test_unauthenticated_requests_do_not_invoke_bedrock(self):
        for path in ("/api/health", "/api/analyze"):
            for authorization in (None, "Bearer wrong", "Basic invalid", "Bearer "):
                headers = {"content-type": "application/json"}
                if authorization:
                    headers["authorization"] = authorization
                response = handler.lambda_handler(self.event(headers=headers, rawPath=path), self.context)
                self.assertEqual(response["statusCode"], 401)
        self.client.converse.assert_not_called()

    def test_missing_auth_configuration_fails_closed(self):
        with patch.object(handler, "API_TOKEN_SHA256", ""):
            self.assertEqual(handler.lambda_handler(self.event(), self.context)["statusCode"], 503)
        self.client.converse.assert_not_called()

    def test_reject_bad_input_before_model_invocation(self):
        events = [self.event(body="{"), self.event(body="[]"), self.event(body="{}"),
                  self.event({"format": "jpeg", "base64": "!invalid!"}),
                  self.event({"format": "jpeg", "base64": base64.b64encode(b"not an image").decode()}),
                  self.event({"format": "gif", "base64": "AAAA"}),
                  self.event({"format": "jpeg", "base64": "A" * (handler.MAX_IMAGE_BYTES * 2)})]
        for event in events:
            with self.subTest(body_length=len(event["body"])):
                self.assertEqual(handler.lambda_handler(event, self.context)["statusCode"], 400)
        self.client.converse.assert_not_called()

    def test_function_url_base64_transport(self):
        event = self.event()
        event["body"] = base64.b64encode(event["body"].encode()).decode()
        event["isBase64Encoded"] = True
        self.assertEqual(handler.lambda_handler(event, self.context)["statusCode"], 200)

    def test_unstructured_model_response_is_not_reported_as_success(self):
        self.client.converse.return_value = {"output": {"message": {"content": [{"text": "not JSON"}]}}}
        self.assertEqual(handler.lambda_handler(self.event(), self.context)["statusCode"], 502)

    def test_bedrock_error_does_not_expose_credentials_or_photo(self):
        failure = Exception("private internal details")
        failure.response = {"Error": {"Code": "AccessDeniedException"}}
        self.client.converse.side_effect = failure
        response = handler.lambda_handler(self.event(), self.context)
        self.assertEqual(response["statusCode"], 503)
        self.assertNotIn("private internal", response["body"])

    def test_routes_and_content_type_reject_without_inference(self):
        self.assertEqual(handler.lambda_handler(self.event(rawPath="/api/health", requestContext={"http": {"method": "GET"}}), self.context)["statusCode"], 200)
        self.assertEqual(handler.lambda_handler(self.event(rawPath="/api/missing"), self.context)["statusCode"], 404)
        self.assertEqual(handler.lambda_handler(self.event(requestContext={"http": {"method": "GET"}}), self.context)["statusCode"], 405)
        self.assertEqual(handler.lambda_handler(self.event(headers={"content-type": "text/plain", "authorization": f"Bearer {self.token}"}), self.context)["statusCode"], 415)
        self.client.converse.assert_not_called()


if __name__ == "__main__":
    unittest.main()
