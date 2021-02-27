import abc
import random
import typing
import time
import logging
import collections
from botocore.exceptions import ClientError

from storagebox import settings
from storagebox.repository.dynamodb import DynamoDBBasedRepository


log = logging.getLogger('storageBox')


class ItemBankRepository(abc.ABC):
    @abc.abstractmethod
    def batch_add_items(self, items: typing.List[str]):
        pass

    @abc.abstractmethod
    def add_item_to_bank(self, item_string: str):
        pass

    @abc.abstractmethod
    def get_item_from_bank(self) -> typing.Optional[str]:
        pass


class ItemBankDynamoDbRepository(ItemBankRepository, DynamoDBBasedRepository):
    @staticmethod
    def __convert_items_to_dynamodb_json(items: typing.List[str]) -> typing.List[typing.Dict]:
        return [
            {
                'item': {
                    'S': item
                }
            }
            for item in items
        ]

    def __group_items(self, items, size) -> collections.deque:
        if len(items) <= size:
            return collections.deque([items])
        batches = collections.deque()
        batches.append(
            items[:size]
        )
        batches.extend(
            self.__group_items(
                items=items[size:],
                size=size
            )
        )
        return batches

    def batch_add_items(self, items: typing.List[str]):
        for item in items:
            assert len(item) < settings.MAX_ALLOWED_ITEM_SIZE, f"Item size cannot exceed {settings.MAX_ALLOWED_ITEM_SIZE} KB"
        dynamodb_json_items = self.__convert_items_to_dynamodb_json(
            items=items
        )
        item_batches = self.__group_items(
            items=dynamodb_json_items,
            size=settings.MAX_ALLOWED_BATCH_SIZE
        )
        consecutive_failures = 0
        while item_batches:
            batch = item_batches.popleft()
            response = self.client.batch_write_item(
                RequestItems={
                    self.table_name: [
                        {
                            'PutRequest': {
                                'Item': item
                            }
                        }
                        for item in batch
                    ]
                }
            )
            if response.get('UnprocessedItems', {}).get('string'):
                unprocessed_batch = [
                    put_request['PutRequest']
                    for put_request in response.get('UnprocessedItems', {}).get('string')
                ]
                item_batches.appendleft(unprocessed_batch)
                consecutive_failures += 1
                backoff_time = settings.BATCH_ADDITION_BACKOFF_TIME * (2**consecutive_failures)
                log.warning("A Batch Was Partially Unprocessed, will wait %s seconds", backoff_time)
                time.sleep(backoff_time)
            else:
                consecutive_failures = 0

    def add_item_to_bank(self, item_string: str):
        self.table.put_item(
            Item={
                'item': item_string
            }
        )

    def get_item_from_bank(self) -> typing.Optional[str]:
        last_evaluated_key = None
        while True:
            if last_evaluated_key:
                response = self.table.scan(
                    Limit=settings.CONCURRENT_FETCH_LIMIT,
                    ExclusiveStartKey=last_evaluated_key
                )
            else:
                response = self.table.scan(
                    Limit=settings.CONCURRENT_FETCH_LIMIT,
                )
            items = response['Items']
            if not len(items):
                return None
            random.shuffle(items)
            for item in items:
                item_string = item['item']
                try:
                    self.table.delete_item(
                        Key={
                            'item': item_string
                        },
                        Expected={
                            'item': {
                                'Value': item_string,
                                'Exists': True
                            }
                        }
                    )
                    return item_string
                except ClientError:
                    log.debug("Item was already deleted, this implies that "
                              "it was fetched by someone else, trying next code")
            else:
                last_evaluated_key = response['LastEvaluatedKey']
