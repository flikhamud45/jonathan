from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
import time
import json
import signal

# Configuration
PROMETHEUS_URL = "http://prometheus.istio-system.svc:9090"  # Adjust this to your Prometheus service URL
VIRTUAL_SERVICE_NAME = "reviews"
VIRTUAL_SERVICE_NAMESPACE = "default"
TARGET_SERVICES_NAME = ["reviews", "ratings", "details"]
TARGET_SERVICE_NAMESPACE = "default"
RETRY_THRESHOLD = 0.1  # Retry disable threshold (e.g., 10% error rate)
CHECK_INTERVAL = 30  # Check every 60 seconds

# Initialize Prometheus connection
print(f"Connecting to Prometheus at {PROMETHEUS_URL}")
prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)


# Initialize Kubernetes client
config.load_incluster_config()  # Use in-cluster configuration
print("Loading in-cluster configuration")
v1 = client.CustomObjectsApi()

# Prometheus query to get error rate for a specific service
def get_error_rate(target_service_name, target_service_namespace):
    query = f'''sum(rate(istio_requests_total{{response_code!="200", destination_service_name="{target_service_name}", destination_service_namespace="{target_service_namespace}"}}[1m]))
               /
               sum(rate(istio_requests_total{{destination_service_name="{target_service_name}", destination_service_namespace="{target_service_namespace}"}}[1m]))'''
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
        vs['spec']['http'][0]['retries'] = {
            "attempts": attempts,
            "perTryTimeout": "2s",
            "retryOn": "5xx"
            } if attempts > 0 else {"attempts": 0}
        
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


def decide_retry_policy(target_service_name, error_rate, current_retry_attempts):
    if error_rate > RETRY_THRESHOLD:
        return 0  # Disable retries
    else:
        return min(current_retry_attempts+1, 5)  # Enable retries

def signal_handler(signum, frame):
    raise KeyboardInterrupt



def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    # Main loop to monitor and update retry policy
    
    prev_time = time.time()
    current_time = time.time()
    retries_data = {service: [] for service in TARGET_SERVICES_NAME}
    error_rate_data = {service: [] for service in TARGET_SERVICES_NAME}
    retries_times = []
    current_retry_attempts_ls = [5] * len(TARGET_SERVICES_NAME)
    print(f"Monitoring error rate for {TARGET_SERVICES_NAME} every {CHECK_INTERVAL} seconds")
    try:
        while True:
            retries_times.append(time.time())
            for i in range(len(TARGET_SERVICES_NAME)):
                target_service_name = TARGET_SERVICES_NAME[i]
                current_retry_attempts = current_retry_attempts_ls[i]

                # Get error rate for the target service
                error_rate = get_error_rate(target_service_name, TARGET_SERVICE_NAMESPACE)
                print(f"Current error rate for {target_service_name}: {error_rate}")

                retries_data[target_service_name].append(current_retry_attempts)
                error_rate_data[target_service_name].append(error_rate)

                # Decide retry policy based on error rate
                new_retry_attempts = decide_retry_policy(target_service_name, error_rate, current_retry_attempts)
                if new_retry_attempts != current_retry_attempts:
                    update_virtual_service(new_retry_attempts)
                    current_retry_attempts_ls[i] = new_retry_attempts
                    print(f"Updated retry policy to {new_retry_attempts} attempts")
                else:
                    print(f"Retry policy remains at {current_retry_attempts} attempts")
                retries_data[target_service_name].append(new_retry_attempts)
                error_rate_data[target_service_name].append(error_rate)

            retries_times.append(time.time())
            # Sleep until next check interval
            current_time = time.time()
            sleep_time = CHECK_INTERVAL - (current_time - prev_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            prev_time = current_time
    except KeyboardInterrupt:
        print("Exiting...")

    data = {
        "retries": retries_data,
        "error_rate": error_rate_data,
        "times": retries_times
    }
    with open('controller_data.json', 'w') as f:
        json.dump(data, f)


if __name__ == "__main__":
    main()
