import boto3


class DynamoDBBasedRepository:
    def __init__(self, table_name):
        self.table_name = table_name
        self.client = boto3.client('dynamodb')
        if not self.table_alreaedy_exists(table_name=self.table_name):
            raise RuntimeError(f"DynamoDB table {self.table_name} does not exist")
        dynamodb = boto3.resource('dynamodb')
        self.table = dynamodb.Table(self.table_name)

    def table_alreaedy_exists(self, table_name) -> bool:
        try:
            self.client.describe_table(TableName=table_name)
            return True
        except self.client.exceptions.ResourceNotFoundException:
            return False
