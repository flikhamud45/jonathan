

# Test parameters (default values are defined after the colons)
TEST_DURATION=45m
QUITE_TIME_SECONDS="${quiet_time_seconds:-11}"
ITERATIONS="${iterations:-1}"
SCRIPT="${script:-k6-script.js}"

kubectl cp ${SCRIPT} $(kubectl get pods -n workload -l app=k6-workload -o custom-columns=:.metadata.name --no-headers):. -n workload
kubectl cp export_gateway $(kubectl get pods -n workload -l app=k6-workload -o custom-columns=:.metadata.name --no-headers):. -n workload
# kubectl exec $(kubectl get pods -n workload -l app=k6-workload -o custom-columns=:.metadata.name --no-headers) -n workload -- sh -c " export GATEWAY_URL=${GATEWAY_URL}"
echo "starting $ITERATIONS iterations of the HTTP test. Each test will run for $TEST_DURATION with $CONNECTIONS connections and $RPS RPS. There will be $QUITE_TIME_SECONDS seconds between each test."
for ((i=1; i <= ITERATIONS; i++)); do
   echo "starting iteration number ${i} of the test"
   python collect_hpa_data.py --save --timestemp --total_time ${TEST_DURATION} --more_time ${QUITE_TIME_SECONDS}s &
   kubectl exec $(kubectl get pods -n workload -l app=k6-workload -o custom-columns=:.metadata.name --no-headers) -n workload -- sh -c " export GATEWAY_URL=${GATEWAY_URL} && k6 run ${SCRIPT}"
   echo "sleeping ${QUITE_TIME_SECONDS} second"
   sleep "$QUITE_TIME_SECONDS"
done
