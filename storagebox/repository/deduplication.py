import abc
import logging
from storagebox.repository.dynamodb import DynamoDBBasedRepository


log = logging.getLogger('storageBox')


class DeduplicationRepository(abc.ABC):
    @abc.abstractmethod
    def get_value_for_deduplication_id(self, deduplication_id: str):
        raise NotImplementedError

    @abc.abstractmethod
    def put_deduplication_id(self, deduplication_id: str, item_string: str):
        raise NotImplementedError


class DeduplicationDynamoDbRepository(DeduplicationRepository, DynamoDBBasedRepository):
    def get_value_for_deduplication_id(self, deduplication_id:str):
        response = self.table.get_item(
            Key={
                'deduplication_id': str(deduplication_id)
            }
        )
        return response.get('Item', {}).get('item_string')  # Returns None if not found

    def put_deduplication_id(self, deduplication_id: str, item_string: str):
        obj = {
            'deduplication_id': deduplication_id,
            'item_string': item_string
        }
        self.table.put_item(  # should only be put if there is no existing entry
            Item=obj,
            Expected={
                'deduplication_id': {
                    'Exists': False
                }
            }
        )
