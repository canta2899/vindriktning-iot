.PHONY: env certs all 

.DEFAULT_GOAL := all 

env:
	@./gen-env

certs:
	@cd ./proxy; ./gen-certs

all:
	@./gen-env
	@cd ./proxy
	@./gen-certs

