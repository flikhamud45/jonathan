
# Test parameters (default values are defined after the colons)
TEST_DURATION="${test_duration:-10m}"
CONNECTIONS="${connections:-100}"
QUITE_TIME_SECONDS="${quiet_time_seconds:-600}"
ITERATIONS="${iterations:-1}"
RPS="${rps:-100}"



echo "starting $ITERATIONS iterations of the HTTP test. Each test will run for $TEST_DURATION with $CONNECTIONS connections and $RPS RPS. There will be $QUITE_TIME_SECONDS seconds between each test."
for ((i=1; i <= ITERATIONS; i++)); do
   echo "starting iteration number ${i} of the test"
   python collect_hpa_data.py --save --timestemp --total_time ${TEST_DURATION} --more_time ${QUITE_TIME_SECONDS}s &
#   kubectl exec $(kubectl get pods -n workload -l app=fortio-workload -o custom-columns=:.metadata.name --no-headers) -n workload -c workload -- fortio load -allow-initial-errors -a -timeout 10000ms -qps "$RPS" -c "$CONNECTIONS" -t "$TEST_DURATION"  http://${GATEWAY_URL}/productpage
   kubectl exec $(kubectl get pods -n workload -l app=fortio-workload -o custom-columns=:.metadata.name --no-headers) -n workload -c workload -- fortio load -allow-initial-errors -a -timeout 10000ms -qps "$RPS" -nocatchup -uniform -c "$CONNECTIONS" -t "$TEST_DURATION"  http://${GATEWAY_URL}/productpage
   echo "sleeping ${QUITE_TIME_SECONDS} second"
   sleep "$QUITE_TIME_SECONDS"
done
