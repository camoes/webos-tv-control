TV_HOST ?= 192.0.2.64
export TV_HOST
SSAP := ./scripts/ssap.py

.PHONY: probe pair info apps volume power power-off wake button netinfo verify

verify:     ## gate de hecho: ssap.py compila, probe.sh válido, pairing.json parsea
	@python3 -m py_compile scripts/ssap.py && echo "  ✓ ssap.py compila"
	@bash -n scripts/probe.sh && echo "  ✓ probe.sh sintaxis OK"
	@if [ -f scripts/pairing.json ]; then python3 -c "import json;json.load(open('scripts/pairing.json'))" && echo "  ✓ pairing.json válido"; else echo "  · sin pairing.json (empareja con make pair)"; fi
	@echo "verify: OK"

probe:      ## reconocimiento de solo lectura (puertos, SSDP)
	@./scripts/probe.sh

pair:       ## empareja con la tele (pide aceptar en pantalla)
	@$(SSAP) register

info:       ## modelo, serie, estado de energía
	@$(SSAP) info
	@$(SSAP) power

apps:       ## apps instaladas con su id
	@$(SSAP) apps

volume:     ## volumen actual (o: make volume V=20)
	@$(SSAP) volume $(V)

power:      ## estado de energía
	@$(SSAP) power

power-off:  ## apagar
	@$(SSAP) power-off

wake:       ## encender por Wake-on-LAN
	@$(SSAP) wake

netinfo:    ## MACs (cableada/Wi-Fi) y guarda TV_MAC para WoL
	@$(SSAP) netinfo

button:     ## tecla del mando: make button B=HOME
	@$(SSAP) button $(B)

ssh:        ## shell en la tele (Developer Mode)
	@ssh tv
