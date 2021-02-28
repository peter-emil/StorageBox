# StorageBox

StorageBox is a python module that you can use to de-duplicate data
among distributed components.

You can think of it as a digital implementation of a physical box. You
put stuff in there and what you put in is exactly what you take out.
No missing and/or duplicated records due to distributed nodes doing concurrent
reads/writes.

For example, let's assume you run a movie store. You have
voucher codes you'd like to hand out to the first 30 users who press
a button. You are concerned that some users might try to get more
than 1 voucher code by exploiting race conditions (maybe clicking the
button from multiple machines at the same time). You're also concerned
that multiple users might get the same voucher code if they're incredibly
unlucky and time their requests at just the right moments.



Here is what StorageBox allows you to do
```
# Setup Code
import storagebox


item_repo = storagebox.ItemBankDynamoDbRepository(table_name="voucher_codes")

deduplication_repo = storagebox.DeduplicationDynamoDbRepository(table_name="storage_box_deduplication_table")


# You can add items to the item repo (for example add list of voucher codes)
item_repo.batch_add_items(voucher_codes)


# You can then assign voucher codes to User IDs
deduplicator = storagebox.Deduplicator(item_repo=item_repo, deduplication_repo=deduplication_repo)

voucher_code = deduplicator.fetch_item_for_deduplication_id(
    deduplication_id=user_id
)
```
And that's it!

- `item_repo`: This is your box, you put in voucher codes and you take them out later. It is responsible
for adding items to the box. It also works with the `deduplication_repo` to make sure that one voucher code gets
taken outside the box for every one unique user.
- `deduplication_repo`: This is what makes sure that no user gets more than one voucher code.
- `deduplicator`: This contains the connecting logic between `item_repo` and `deduplication_repo`

As long as you use a suitable `deduplication_id`, all race conditions
and data hazards will be taken care of for you. Examples of suitable 
candidates for `deduplication_id` can be User ID, IP Address, 
Email Address or anything that works best with your application.


## Prerequisites
To use StorageBox, you need the following already set up.

- An ItemBank DynamoDB Table, The current implementation requires the table to have 1 column
called `item`. This is where you will store items (in the case of the example:
voucher codes).
- A Deduplication DynamoDB Table, This will be used by `StorageBox` to achieve idempotency, 
that is, to make sure that if you call `fetch_item_for_deduplication_id` multiple times with
the same `deduplication_id`, you will always get the same result.

If you prefer to use something else other than DynamoDB, you can implement your own `ItemBankRepository`
and/or `DeduplicationRepository` for any other backend. This implementation will have to implement
the already established Abstract class. You'll also need to read the blogpost at the bottom of this
 README to understand how the storagebox algoritm works. If you do that, contributions are welcome!


## Installation
```
pip install storagebox
```


## Other Example Use Cases
Hosting a big event and only have 10,300 seats that would be booked in the first few minutes?
```
# Before the event, add 10,300 numbers to the bank
item_repo.batch_add_items([str(i) for i in range(10300)])

# From your webserver
assignment_number = deduplicator.fetch_item_for_deduplication_id(
    deduplication_id=email
)
```

Are you an influencer and only have 5000 people to give special referral links to? (First 5000
people who click the link in the description get a free something!)
```
# Before you post your content
item_repo.batch_add_items(referral_links_list)

# From your webserver
referral_link = deduplicator.fetch_item_for_deduplication_id(
    deduplication_id=ip_address
)
```

Are you organizing online classes for your 150 students, you're willing to host 3 classes (50 students each)
 but you'd like to be sure that no student attends more than 1 class?
```
# Before you host your classes
class_1_codes = storagebox.ItemBankDynamoDbRepository(table_name="class_1_codes")
class_2_codes = storagebox.ItemBankDynamoDbRepository(table_name="class_2_codes")
class_3_codes = storagebox.ItemBankDynamoDbRepository(table_name="class_3_codes")
deduplication_repo = storagebox.DeduplicationDynamoDbRepository(table_name="myonline_classes_deduplication_table")

class_1_codes.([str(i) for i in range(0, 50)])
class_2_codes.([str(i) for i in range(50, 100)])
class_3_codes.([str(i) for i in range(100, 150)])

# From your webserver
deduplicators = {
    'class_1': storagebox.Deduplicator(item_repo=class_1_codes, deduplication_repo=deduplication_repo),
    'class_2': storagebox.Deduplicator(item_repo=class_2_codes, deduplication_repo=deduplication_repo),
    'class_3': storagebox.Deduplicator(item_repo=class_3_codes, deduplication_repo=deduplication_repo),
}

deduplicator[requested_class].fetch_item_for_deduplication_id(
    deduplication_id=student_id
)

```

# How It Works
A blogpost explaining how `storagebox` works is available [here](https://blog.peteremil.com/2021/02/realtime-distributed-deduplication-how.html)