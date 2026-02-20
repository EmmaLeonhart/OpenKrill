.PHONY: build deploy logs shell clean port-forward

IMAGE_NAME=krill:latest
NAMESPACE=krill

build:
	docker build -t $(IMAGE_NAME) .

deploy:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/secret.yaml -n $(NAMESPACE)
	kubectl apply -f k8s/configmap.yaml -n $(NAMESPACE)
	kubectl apply -f k8s/service.yaml -n $(NAMESPACE)
	kubectl apply -f k8s/statefulset.yaml -n $(NAMESPACE)

logs:
	kubectl logs -f krill-0 -n $(NAMESPACE)

shell:
	kubectl exec -it krill-0 -n $(NAMESPACE) -- /bin/bash

port-forward:
	kubectl port-forward pod/krill-0 18789:18789 -n $(NAMESPACE)

status:
	kubectl get pods -n $(NAMESPACE) -w
