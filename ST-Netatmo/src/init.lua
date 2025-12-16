-- 📢 MARQUEUR DE VERSION : V11 (ULTIMATE : WATCHDOG + MONITORING)
local log = require "log"
log.info("🔥🔥🔥 CODE V11 CHARGÉ : LA TOTALE ! 🔥🔥🔥")

local Driver = require "st.driver"
local capabilities = require "st.capabilities"
local http = require "cosock.socket.http"
local json = require "dkjson"
local ltn12 = require "ltn12"
local socket = require "cosock.socket"

-- 🛠️ CONFIGURATION IP (Ton Pi)
local PI_IP = "192.168.1.42"
local PI_PORT = 5000

-- ⏱️ DELAI DE POLLING (EN SECONDES)
local POLLING_INTERVAL = 300 -- 5 minutes

-- MAPPING DES MODES
local MODE_MAP = { ["heat"] = "schedule", ["auto"] = "schedule", ["eco"] = "away", ["off"] = "hg" }
local REVERSE_MODE_MAP = { ["schedule"] = "auto", ["away"] = "eco", ["hg"] = "off" }

-- FONCTIONS UTILITAIRES
local function find_device_by_dni(driver, dni)
  for _, device in ipairs(driver:get_devices()) do
    if device.device_network_id == dni then return device end
  end
  return nil
end

-- 🚦 GESTION DES VOYANTS (TUILES)
local function update_connection_status(driver, status_local, status_cloud)
    local bridge = find_device_by_dni(driver, "netatmo-bridge-001")
    if not bridge then return end

    local comp_local = bridge.profile.components["local_connection"]
    local comp_cloud = bridge.profile.components["cloud_connection"]

    -- Mise à jour Liaison LOCALE (Hub <-> Pi)
    if comp_local then
        if status_local then
            bridge:emit_component_event(comp_local, capabilities.contactSensor.contact.closed())
        else
            bridge:emit_component_event(comp_local, capabilities.contactSensor.contact.open())
        end
    end

    -- Mise à jour Liaison CLOUD (Pi <-> Netatmo)
    if comp_cloud then
        if status_cloud then
            bridge:emit_component_event(comp_cloud, capabilities.contactSensor.contact.closed())
        else
            bridge:emit_component_event(comp_cloud, capabilities.contactSensor.contact.open())
        end
    end
    
    -- Gestion globale Online/Offline (Grisé ou pas)
    if status_local == false then
        bridge:offline() 
    else
        bridge:online()
    end
end

local function send_post(path, data)
  local url = string.format("http://%s:%s/netatmo/%s", PI_IP, PI_PORT, path)
  local body_str = json.encode(data)
  local response_body = {}
  local res, code, response_headers = http.request{
    url = url,
    method = "POST",
    headers = { ["Content-Type"] = "application/json", ["Content-Length"] = string.len(body_str) },
    source = ltn12.source.string(body_str),
    sink = ltn12.sink.table(response_body)
  }
  return code
end

local function fetch_state(force)
  local endpoint = force and "refresh" or "state"
  local url = string.format("http://%s:%s/netatmo/%s", PI_IP, PI_PORT, endpoint)
  local method = force and "POST" or "GET"
   
  local response_body = {}
  
  -- Timeout court (5s) pour détecter rapidement si le Pi est éteint
  http.TIMEOUT = 5 
  
  local res, code, response_headers = http.request{
    url = url,
    method = method,
    sink = ltn12.sink.table(response_body)
  }
  
  -- DIAGNOSTIC RÉSEAU
  if code == nil then
    log.error("❌ ERREUR RÉSEAU LOCAL : Le Hub ne joint pas le Pi")
    return nil, 0
  end

  if code ~= 200 then
    log.error("❌ ERREUR API DISTANTE : Code " .. tostring(code))
    return nil, code
  end

  return json.decode(table.concat(response_body)), 200
end

local function sync_devices(driver, force)
  log.info("🔄 Sync en cours...")
  local state, code = fetch_state(force)
   
  -- 🩺 DIAGNOSTIC SANTÉ
  if state == nil then
      if code == 0 then
          -- Local KO / Cloud Inconnu
          update_connection_status(driver, false, false)
      elseif code == 502 or code == 503 then
          -- Local OK / Cloud KO
          update_connection_status(driver, true, false)
      else
          update_connection_status(driver, false, false)
      end
      return 
  end

  -- Tout va bien
  update_connection_status(driver, true, true)
   
  if not state.homes or #state.homes == 0 then 
    log.error("❌ Erreur structure JSON")
    return 
  end
   
  if force then log.info("⚡ Refresh manuel ou forcé effectué") end

  local home = state.homes[1]
  local home_id = home.id

  -- 1. PONT NETATMO
  local bridge_dni = "netatmo-bridge-001"
  local bridge = find_device_by_dni(driver, bridge_dni)

  if not bridge then
    log.info("🆕 Création du Pont Netatmo...")
    local metadata = {
      type = "LAN",
      device_network_id = bridge_dni,
      label = "Netatmo Bridge",
      profile = "netatmo-bridge",
      manufacturer = "Netatmo",
      model = "Bridge",
      vendor_provided_label = "Netatmo Bridge"
    }
    driver:try_create_device(metadata)
  else
    bridge:emit_event(capabilities.thermostatMode.supportedThermostatModes({"off", "eco", "auto"}))
    local reset_comp = bridge.profile.components["forced_schedule"]
    if reset_comp then bridge:emit_component_event(reset_comp, capabilities.switch.switch.off()) end
    
    local current_mode = "schedule"
    if home.thermostat and home.thermostat.mode then current_mode = home.thermostat.mode end
    local st_mode = REVERSE_MODE_MAP[current_mode] or "auto"
    bridge:emit_event(capabilities.thermostatMode.thermostatMode(st_mode))
  end

  -- 2. PIÈCES
  if bridge then 
      for _, room in ipairs(home.rooms) do
        local dni = string.format("netatmo-%s", room.id)
        local existing = find_device_by_dni(driver, dni)
        
        if not existing then
          log.info("🆕 Création de la pièce : " .. room.name)
          local metadata = {
            type = "LAN",
            device_network_id = dni,
            label = room.name,
            profile = "netatmo-valve",
            manufacturer = "Netatmo",
            model = "NRV",
            parent_device_id = bridge.id,
            vendor_provided_label = room.name
          }
          driver:try_create_device(metadata)
        else
          existing:online() -- La pièce est vivante
          if room.temperature then
            existing:emit_event(capabilities.temperatureMeasurement.temperature({value = room.temperature, unit = "C"}))
          end
          if room.setpoint then
            existing:emit_event(capabilities.thermostatHeatingSetpoint.heatingSetpoint({value = room.setpoint, unit = "C"}))
          end
          existing:set_field("home_id", home_id, {persist = true})
          existing:set_field("room_id", room.id, {persist = true})
        end
      end
  end
  log.info("✅ Données synchronisées.")
end

-- ⏰ GESTION DU TIMER (WATCHDOG)
local function ensure_timer_running(driver)
    local bridge = find_device_by_dni(driver, "netatmo-bridge-001")
    if not bridge then
         for _, d in ipairs(driver:get_devices()) do
             if d.profile.id == "netatmo-bridge" then bridge = d break end
         end
    end

    if not bridge then return end

    if bridge:get_field("timer_active") == true then return end

    log.info("🐶 WATCHDOG : Démarrage du timer !")
    bridge:set_field("timer_active", true)
    
    bridge.thread:call_on_schedule(POLLING_INTERVAL, function()
        log.info("⏰ Polling automatique...")
        sync_devices(driver, false)
    end)
    
    log.info("✅ Timer actif.")
    bridge.thread:call_with_delay(2, function() sync_devices(driver, false) end)
end

-- HANDLERS CAPACITÉS
local function handle_setpoint(driver, device, command)
  local setpoint = command.args.setpoint
  local home_id = device:get_field("home_id")
  local room_id = device:get_field("room_id")
  if home_id and room_id then
    log.info(string.format("🎮 Consigne %.1f°C pour %s", setpoint, device.label))
    device:emit_event(capabilities.thermostatHeatingSetpoint.heatingSetpoint({value = setpoint, unit = "C"}))
    send_post("set_temp", { home_id = home_id, room_id = room_id, temp = setpoint })
    -- On force un rafraichissement rapide pour voir l'effet
    device.thread:call_with_delay(2, function() sync_devices(driver, false) end)
  end
end

local function handle_mode(driver, device, command)
  local mode = command.args.mode
  log.info("🎮 Mode : " .. tostring(mode))
  local netatmo_mode = MODE_MAP[mode]
  if not netatmo_mode then return end
  device:emit_event(capabilities.thermostatMode.thermostatMode(mode))
  local state, _ = fetch_state(false)
  if state and state.homes and state.homes[1] then
    local home_id = state.homes[1].id
    send_post("set_mode", { home_id = home_id, mode = netatmo_mode })
  end
end

local function handle_reset_switch(driver, device, command)
  local component = device.profile.components["forced_schedule"]
  if command.command == "on" then
    log.info("🔙 SWITCH RESET : Retour au planning !")
    if component then device:emit_component_event(component, capabilities.switch.switch.on()) end
    local state, _ = fetch_state(false)
    if state and state.homes and state.homes[1] then
      local home_id = state.homes[1].id
      send_post("set_mode", { home_id = home_id, mode = "schedule" })
      device:emit_event(capabilities.thermostatMode.thermostatMode("auto"))
    end
    socket.sleep(1.0)
    if component then device:emit_component_event(component, capabilities.switch.switch.off()) end
  else
    if component then device:emit_component_event(component, capabilities.switch.switch.off()) end
  end
end

local function refresh_handler(driver, device)
  log.info("🖱️ Refresh manuel demandé")
  ensure_timer_running(driver)
  sync_devices(driver, true)
end

local function discovery_handler(driver, _, should_continue)
  log.info("🔍 Discovery (Scan)...")
  sync_devices(driver, false) 
  ensure_timer_running(driver)
end

local function device_doconfigure(driver, device)
    log.info("🔧 Configuration : " .. device.label)
    if device.device_network_id == "netatmo-bridge-001" or device.profile.id == "netatmo-bridge" then
        ensure_timer_running(driver)
    end
end

local function device_lifecycle_fallback(driver, device)
    if device.device_network_id == "netatmo-bridge-001" or device.profile.id == "netatmo-bridge" then
        ensure_timer_running(driver)
    end
end

local netatmo_driver = Driver("netatmo_driver", {
  discovery = discovery_handler,
  lifecycle = {
    init = device_lifecycle_fallback,
    added = device_lifecycle_fallback,
    doConfigure = device_doconfigure,
    infoChanged = device_lifecycle_fallback
  },
  capability_handlers = {
    [capabilities.refresh.ID] = { [capabilities.refresh.commands.refresh.NAME] = refresh_handler },
    [capabilities.thermostatHeatingSetpoint.ID] = { [capabilities.thermostatHeatingSetpoint.commands.setHeatingSetpoint.NAME] = handle_setpoint },
    [capabilities.thermostatMode.ID] = { [capabilities.thermostatMode.commands.setThermostatMode.NAME] = handle_mode },
    [capabilities.switch.ID] = { 
      [capabilities.switch.commands.on.NAME] = handle_reset_switch, 
      [capabilities.switch.commands.off.NAME] = handle_reset_switch 
    }
  }
})

netatmo_driver:run()