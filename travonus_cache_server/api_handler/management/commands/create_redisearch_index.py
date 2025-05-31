from django.conf import settings
import redis
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or remove Redisearch index for Flight model"

    def add_arguments(self, parser):
        parser.add_argument(
            "--remove",
            action="store_true",
            help="Remove the Redisearch index instead of creating it",
        )

    def handle(self, *args, **kwargs):

        redis_client = redis.StrictRedis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

        index_name = "result_cache_idx"

        if kwargs["remove"]:
            try:
                redis_client.ft(index_name).dropindex(delete_documents=False)
                self.stdout.write(
                    self.style.SUCCESS("Successfully removed Redisearch index")
                )
            except redis.exceptions.ResponseError as e:
                self.stdout.write(self.style.ERROR(f"Error removing index: {e}"))
        else:
            try:
                redis_client.ft(index_name).create_index(
                    # Schema
                    (
                        NumericField("$.total_fare", as_name="total_fare"),
                        NumericField("$.segments[0].origin.departure_time", as_name="first_departure_time"),
                        TagField("$.is_refundable", as_name="is_refundable"),
                        TextField("$.meta_data.segments[0].origin", as_name="origin"),
                        TextField(
                            "$.meta_data.segments[0].destination", as_name="destination"
                        ),
                        TagField(
                            "$.meta_data.segments[0].departure_date",
                            as_name="departure_date",
                        ),
                    ),
                    definition=IndexDefinition(
                        prefix=["flight_cache:"], index_type=IndexType.JSON
                    ),
                )
                self.stdout.write(
                    self.style.SUCCESS("Successfully created Redisearch index")
                )
            except redis.exceptions.ResponseError as e:
                self.stdout.write(self.style.ERROR(f"Error creating index: {e}"))
