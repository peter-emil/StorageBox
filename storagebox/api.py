import logging
import typing
from botocore.exceptions import ClientError
from storagebox import settings
from storagebox import repository


log = logging.getLogger('storageBox')
log.setLevel(settings.DEFAULT_LOGGING_LEVEL)


class Deduplicator:
    def __init__(self, item_repo, deduplication_repo):
        self.item_repo = item_repo
        self.deduplication_repo = deduplication_repo

    def fetch_item_for_deduplication_id(self, deduplication_id):
        item_string = self.item_repo.get_item_from_bank()
        if item_string is None:
            return item_string
        try:
            self.deduplication_repo.put_deduplication_id(
                deduplication_id=deduplication_id,
                item_string=item_string
            )
            return item_string
        except ClientError:
            log.debug("deduplication_id is already assigned, will check if I"
                      " should return item_string %s to the bank", item_string)
            existing_item_string = self.deduplication_repo.get_value_for_deduplication_id(
                deduplication_id=deduplication_id
            )
            if existing_item_string != item_string:
                self.item_repo.add_item_to_bank(
                    item_string=item_string
                )
                log.debug("Item %s was returned", item_string)
                return existing_item_string
            return item_string

    def add_items_to_bank(self, items: typing.List[str]):
        self.item_repo.batch_add_items(
            items=items
        )
