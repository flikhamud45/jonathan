PROJECT_NAME ?= "spry-water-434415-u2" # GCP Project name
DEPLOYMENT_NAME ?= "where-is-my-money" # Deployment name in GCP Deployment Manager
ZONE ?= "us-central1-c"

send_query:
	curl -s "http://${GATEWAY_URL}/productpage" | grep -o "<title>.*</title>"

deploy-gke: gke-login create-gke-cluster kubectx deploy-bookinfo deploy-istio deploy-fortio deploy-monitoring create-gateway deploy-version deploy-retries deploy-hpa

destroy-gke:
	bash istio/samples/bookinfo/platform/kube/cleanup.sh
	gcloud container clusters delete $(DEPLOYMENT_NAME) --zone $(ZONE)

gke-login:
	gcloud auth login
	gcloud config set project $(PROJECT_NAME)

create-gke-cluster:
	gcloud container clusters create $(DEPLOYMENT_NAME) \
	--zone $(ZONE) \
	--num-nodes 4 \
	--machine-type n2-standard-16

kubectx:
	gcloud container clusters get-credentials $(DEPLOYMENT_NAME) --zone $(ZONE)

deploy-bookinfo:
	kubectl label namespace default istio-injection=enabled
	kubectl apply -f istio/samples/bookinfo/platform/kube/bookinfo.yaml

deploy-istio:
	kubectl get crd gateways.gateway.networking.k8s.io &> /dev/null || { kubectl kustomize "github.com/kubernetes-sigs/gateway-api/config/crd?ref=v1.1.0" | kubectl apply -f -; }
	./istio/bin/istioctl install


deploy-fortio:
	# Get the list of all nodes
	@nodes=$$(kubectl get nodes --no-headers -o custom-columns=":metadata.name"); \
	for node in $$nodes; do \
		pods=$$(kubectl get pods --field-selector spec.nodeName=$$node --no-headers); \
		if [ -z "$$pods" ]; then \
			echo "Labeling node $$node with group=workload"; \
			kubectl label node $$node group=workload; \
			break; \
		fi; \
	done
	kubectl create ns workload --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f fortio/loadGenerator.yaml


deploy-monitoring:
	kubectl apply -f istio/samples/addons/prometheus.yaml
	kubectl apply -f istio/samples/addons/grafana.yaml
#	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
#	helm repo update
#	helm install sm -f ./monitoring-values.yaml prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace
#	kubectl apply -f dashboards/


create-gateway:
	kubectl apply -f istio/samples/bookinfo/networking/bookinfo-gateway.yaml # this includes retry for the gateway
	echo please run "source export_gateway"

deploy-versions:
	kubectl apply -f istio/samples/bookinfo/networking/destination-rule-all.yaml

deploy-retries:
	kubectl apply -f virtual-service-reviews.yaml
	kubectl apply -f virtual-service-ratings.yaml
	kubectl apply -f virtual-service-details.yaml

deploy-hpa:
	kubectl apply -f default-details-hpa.yaml
	kubectl apply -f default-productpage-hpa.yaml
	kubectl apply -f default-ratings-hpa.yaml
	kubectl apply -f slow-reviews-v1-hpa.yaml
	kubectl apply -f slow-reviews-v2-hpa.yaml
	kubectl apply -f slow-reviews-v3-hpa.yaml

test:
	bash ./run-http-test.sh

