import datetime
from logging import getLogger
from opencensus.ext.azure.log_exporter import AzureLogHandler

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import SubscriptionClient

from azure.cli.core import get_default_cli

import azure.functions as func

logging = getLogger(__name__)
logging.addHandler(AzureLogHandler())


credential = DefaultAzureCredential()

cli = get_default_cli()


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = (
        datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    )

    # logging.info("Python timer trigger function ran at %s", utc_timestamp)
    subscription_client = SubscriptionClient(credential=credential)
    subscriptions = subscription_client.subscriptions.list()
    for subscription in subscriptions:
        logging.info("Subscription ID: %s", subscription.subscription_id)
        cli.invoke(["aks", "list", "--subscription", subscription.subscription_id])


# insert main function here
if __name__ == "__main__":
    main(None)
