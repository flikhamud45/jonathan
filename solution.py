from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
import time

# Configuration
PROMETHEUS_URL = "http://prometheus.istio-system.svc:9090"  # Adjust this to your Prometheus service URL
VIRTUAL_SERVICE_NAME = "reviews"
VIRTUAL_SERVICE_NAMESPACE = "default"
TARGET_SERVICE_NAME = "reviews"
TARGET_SERVICE_NAMESPACE = "default"
RETRY_THRESHOLD = 0.1  # Retry disable threshold (e.g., 10% error rate)
CHECK_INTERVAL = 60  # Check every 60 seconds

# Initialize Prometheus connection
print(f"Connecting to Prometheus at {PROMETHEUS_URL}")
prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)


# Initialize Kubernetes client
config.load_incluster_config()  # Use in-cluster configuration
print("Loading in-cluster configuration")
v1 = client.CustomObjectsApi()

# Prometheus query to get error rate for a specific service
def get_error_rate():
    query = f'''sum(rate(istio_requests_total{{response_code=~"5.*", destination_service_name="{TARGET_SERVICE_NAME}", destination_service_namespace="{TARGET_SERVICE_NAMESPACE}"}}[1m]))
               /
               sum(rate(istio_requests_total{{destination_service_name="{TARGET_SERVICE_NAME}", destination_service_namespace="{TARGET_SERVICE_NAMESPACE}"}}[1m]))'''
    result = prom.custom_query(query)
    if result and len(result) > 0:
        return float(result[0]['value'][1])
    return 0.0

# Update VirtualService retry policy
def update_virtual_service(attempts):
    try:
        vs = v1.get_namespaced_custom_object(
            group="networking.istio.io",
            version="v1beta1",
            namespace=VIRTUAL_SERVICE_NAMESPACE,
            plural="virtualservices",
            name=VIRTUAL_SERVICE_NAME
        )
        
        # Modify retries in VirtualService
        vs['spec']['http'][0]['retries'] = {"attempts": attempts, "perTryTimeout": "2s"}
        
        # Update the VirtualService
        v1.patch_namespaced_custom_object(
            group="networking.istio.io",
            version="v1beta1",
            namespace=VIRTUAL_SERVICE_NAMESPACE,
            plural="virtualservices",
            name=VIRTUAL_SERVICE_NAME,
            body=vs
        )
        print(f"Updated VirtualService {VIRTUAL_SERVICE_NAME} retries to {attempts} attempts")
    except Exception as e:
        print(f"Error updating VirtualService: {e}")


def decide_retry_policy(error_rate, current_retry_attempts):
    if error_rate > RETRY_THRESHOLD:
        return 1  # Disable retries
    else:
        return 5  # Enable retries with 5 attempts


def main():
    # Main loop to monitor and update retry policy
    prev_time = time.time()
    current_time = time.time()
    current_retry_attempts = 0
    print(f"Monitoring error rate for {TARGET_SERVICE_NAME} every {CHECK_INTERVAL} seconds")
    while True:
        error_rate = get_error_rate()
        print(f"Current error rate for {TARGET_SERVICE_NAME}: {error_rate}")

        # Decide retry policy based on error rate
        new_retry_attempts = decide_retry_policy(error_rate, current_retry_attempts)
        if new_retry_attempts != current_retry_attempts:
            update_virtual_service(new_retry_attempts)
            current_retry_attempts = new_retry_attempts
            print(f"Updated retry policy to {current_retry_attempts} attempts")
        else:
            print(f"Retry policy remains at {current_retry_attempts} attempts")

        # Sleep until next check interval
        current_time = time.time()
        sleep_time = CHECK_INTERVAL - (current_time - prev_time)
        if sleep_time > 0:
            time.sleep(sleep_time)
        prev_time = current_time

if __name__ == "__main__":
    main()
