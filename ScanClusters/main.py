import logging
import semver

from functools import cache
from opencensus.ext.azure.log_exporter import AzureLogHandler

from azure.identity import DefaultAzureCredential
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.subscription import SubscriptionClient
import azure.mgmt.resourcegraph as arg

import azure.functions as func

logging.root.addHandler(AzureLogHandler())


@cache
def latest_version(region="westeurope"):
    """Get the latest version of Kubernetes available in a region."""
    credential = DefaultAzureCredential()
    subscription_client = SubscriptionClient(credential)
    sub_list = subscription_client.subscriptions.list()
    first_sub = next(sub_list)
    container_service_client = ContainerServiceClient(
        credential, subscription_id=first_sub.subscription_id
    )
    orchestrator_list = container_service_client.container_services.list_orchestrators(
        location=region,
        resource_type="managedClusters",
    )
    versions = [
        semver.VersionInfo.parse(x.orchestrator_version)
        for x in orchestrator_list.orchestrators
        if not x.is_preview
    ]
    return max(versions)


class Cluster:
    def __init__(self, id, region, version):
        self.id = id
        self.region = region
        self.version = version

    def __init__(self, args):
        self.id = args["id"]
        self.region = args["location"]
        self.version = semver.VersionInfo.parse(args["version"])

    def __repr__(self):
        return f"Cluster({self.id}, {self.region}, {self.version})"

    def __str__(self):
        return f"{self.id} ({self.region}): {self.version}, delta={self.delta}"

    def __eq__(self, other):
        return self.id == other.id

    @property
    def delta(self):
        return latest_version(self.region).minor - self.version.minor


def main(timer: func.TimerRequest) -> None:
    latest_version.cache_clear()
    credential = DefaultAzureCredential()
    argClient = arg.ResourceGraphClient(credential)
    argQueryOptions = arg.models.QueryRequestOptions(result_format="objectArray")

    strQuery = 'Resources | where type == "microsoft.containerservice/managedclusters" | project id, location, version = properties.kubernetesVersion'
    argQuery = arg.models.QueryRequest(query=strQuery, options=argQueryOptions)
    argResults = argClient.resources(argQuery)

    clusters = [Cluster(cluster) for cluster in argResults.data]
    logging.info(f"Found {len(clusters)} clusters")
    logging.info(f"{clusters}")
    for cluster in clusters:
        if cluster.delta > 2:
            logging.info(f"Cluster {cluster} is about to run out of date")
        elif cluster.delta > 3:
            logging.warning(f"Cluster {cluster} is out of date")
        else:
            logging.debug(f"Cluster {cluster} is up to date")


# insert main function here
if __name__ == "__main__":
    main(None)
