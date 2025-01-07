import boto3
import json


class BedrockClient:
    def __init__(self, model_id: str):
        self.client = boto3.client(
            service_name="bedrock-runtime", region_name="ap-northeast-1"
        )
        self.model_id = model_id

    def invoke_model(self, body: dict):
        """
        Synchronously invoke the Bedrock model

        Args:
            body: The request body for the model

        Returns:
            Dict containing the model's response
        """
        response = self.client.invoke_model(
            body=json.dumps(body),
            modelId=self.model_id,
            accept="application/json",
            contentType="application/json",
        )
        return response
