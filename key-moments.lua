obs = obslua

local version=1.2

streaming_output_options = { "--Disabled--", "Console", "YouTube" }
streaming_output = streaming_output_options[2]
streaming = { start_time=0, key_moments = { } }

recording_output_options = { "--Disabled--", "Console", "File" }
recording_output = recording_output_options[2]
recording = { start_time=0, key_moments = { } }
prompt = true
key_moment_lead_in = 2
min_key_moment_duration = 60

description = ""
key_moment_names = { }
key_scenes = { }


local ffi = require("ffi")  -- Load FFI module (instance)

local user32 = ffi.load("user32")   -- Load User32 DLL handle

ffi.cdef([[
enum{
    MB_OK = 0x00000000L,
    MB_ICONINFORMATION = 0x00000040L
};
typedef void* HANDLE;
typedef HANDLE HWND;
typedef const char* LPCSTR;
typedef unsigned UINT;
int MessageBoxA(HWND, LPCSTR, LPCSTR, UINT);
]]) -- Define C -> Lua interpretation

function compile_key_momemnts(obj)
	-- Remove duplicate key-moments
	for i in pairs(obj.key_moments) do
		if table.getn(obj.key_moments[i]) == 2 and table.getn(obj.key_moments[i-1]) == 2 and obj.key_moments[i-1][2] == obj.key_moments[i][2] then
			table.remove(obj.key_moments, i)
		end
	end
	
	-- Turn each key-moment into a string
	for i, item in ipairs(obj.key_moments) do
		if table.getn(item) == 2 then
			local delta = item[1]
			if item[1] > key_moment_lead_in then
				delta = item[1] - key_moment_lead_in
			end

			local hh = math.floor(delta / 60 / 60)
			local mm = math.floor(delta / 60) % 60
			local ss = delta % 60

			obj.key_moments[i] = string.format("%02d:%02d:%02d", hh, mm, ss) .. " " .. item[2]
		elseif table.getn(item) == 1 then
			obj.key_moments[i] = item[1]
		else
			obj.key_moments[i] = ""
		end
	end
	return table.concat(obj.key_moments, "\n")
end

function update_key_moments(obj, scene_name)
	if table.getn(obj.key_moments) > 0 and key_scenes[scene_name] ~= "" and obj.key_moments[table.maxn(obj.key_moments)][2] ~= key_scenes[scene_name] then
		for key_scene, key_moment in pairs(key_scenes) do
			if scene_name == key_scene then
				local timestamp = os.difftime(os.time(), obj.start_time)
				if os.difftime(timestamp, obj.key_moments[table.maxn(obj.key_moments)][1]) < min_key_moment_duration then
					-- Update previous 'key moment' to this scene name
					obj.key_moments[table.maxn(obj.key_moments)][2] = key_moment
				else
					-- Insert new 'key moment'
					table.insert(obj.key_moments, { timestamp, key_moment } )
				end
				break
			end
		end
	end
end

function on_event(event)
	if event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED and streaming_output ~= streaming_output_options[1] then
		streaming.start_time = os.time()
		streaming.key_moments = { { }, { description }, { }, { 0, key_moment_names[1] } }
	elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED and recording_output ~= recording_output_options[1] then
		recording.start_time = os.time()
		recording.key_moments = { { }, { description }, { }, { 0, key_moment_names[1] } }
	elseif event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED and streaming.start_time > 0 then
		print("Streaming Key Moments")
		print(compile_key_momemnts(streaming))
		streaming = { start_time = 0, key_moments = { } }
		if prompt == true then
			user32.MessageBoxA(nil, "Tools->Scripts->Script Log\n\nCopy the Key Moments and paste them into the YouTube video description.", "Key Moments", ffi.C.MB_OK)   -- Call C function 'MessageBoxA' from User32
		end
	elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED and recording.start_time > 0 then
		print("Recording Key Moments")
		print(compile_key_momemnts(recording))
		recording = { start_time = 0, key_moments = { } }
		if prompt == true then
			user32.MessageBoxA(nil, "Tools->Scripts->Script Log\n\nCopy the Key Moments and paste them into the YouTube video description.", "Key Moments", ffi.C.MB_OK)   -- Call C function 'MessageBoxA' from User32
		end
	elseif event == obs.OBS_FRONTEND_EVENT_SCENE_CHANGED and (streaming.start_time > 0 or recording.start_time > 0) then
		local scene = obs.obs_frontend_get_current_scene()
		local scene_name = obs.obs_source_get_name(scene)
		if streaming.start_time > 0 then
			update_key_moments(streaming, scene_name)
		end
		if recording.start_time > 0 then
			update_key_moments(recording, scene_name)
		end
	end
end

local function has_value (tab, val)
    for index, value in ipairs(tab) do
        if value == val then
            return true
        end
    end

    return false
end

function key_moment_names_modified(props, property, settings)
	local scene_names = obs.obs_frontend_get_scene_names()
	if scene_names ~= nil then
		for _, scene_name in ipairs(scene_names) do
			local p = obs.obs_properties_get(props, scene_name)
			add_key_moment_list(p, false)
		end
	end
	return true
end

function add_key_moment_list(p, required)
	obs.obs_property_list_clear(p)
	if not required then
		obs.obs_property_list_add_string(p, "", "")
	end
	for _, key_moment_name in ipairs(key_moment_names) do
		obs.obs_property_list_add_string(p, key_moment_name, key_moment_name)
	end
end

function on_property_modified(props, property, settings)
	local has_output = streaming_output ~= streaming_output_options[1] or recording_output ~= recording_output_options[1]
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "prompt"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_moment_lead_in"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "min_key_moment_duration"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "description"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_moment_names"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_scenes"), has_output)
	return true
end

function script_properties()
	has_output = streaming_output ~= streaming_output_options[1] or recording_output ~= recording_output_options[1]
	local props = obs.obs_properties_create()

	local p = obs.obs_properties_add_list(props, "streaming_output", "Streaming Output", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, on_property_modified)
	for _, option in ipairs(streaming_output_options) do
		obs.obs_property_list_add_string(p, option, option)
	end

	p = obs.obs_properties_add_list(props, "recording_output", "Recording Output", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, on_property_modified)
	for _, option in ipairs(recording_output_options) do
		obs.obs_property_list_add_string(p, option, option)
	end

	p = obs.obs_properties_add_bool(props, "prompt", "Display Prompts")
	obs.obs_property_set_enabled(p, has_output)

	p = obs.obs_properties_add_int_slider(props, "key_moment_lead_in", "Key Moment Lead In", 0, 10, 1)
	obs.obs_property_set_enabled(p, has_output)

	p = obs.obs_properties_add_int_slider(props, "min_key_moment_duration", "Min Key-Moment Duration", 10, 300, 10)
	obs.obs_property_set_enabled(p, has_output)

	p = obs.obs_properties_add_text(props, "description", "Video Description", obs.OBS_TEXT_MULTILINE)
	obs.obs_property_set_enabled(p, has_output)

	p = obs.obs_properties_add_editable_list(props, "key_moment_names", "Key Moments", obs.OBS_EDITABLE_LIST_TYPE_STRINGS, nil, nil)
	obs.obs_property_set_enabled(p, has_output)
	obs.obs_property_set_modified_callback(p, key_moment_names_modified)

	local grp = obs.obs_properties_create()
	local scene_names = obs.obs_frontend_get_scene_names()
	if scene_names ~= nil then
		for _, scene_name in ipairs(scene_names) do
			local name = obs.obs_source_get_name(scene);
			p = obs.obs_properties_add_list(grp, scene_name, scene_name, obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
			obs.obs_property_set_enabled(p, has_output)
			add_key_moment_list(p, false)
		end
	end
	obs.obs_properties_add_group(props, "key_scenes", "Key Scenes", obs.OBS_GROUP_NORMAL, grp)

	return props
end

function script_defaults(settings)
	obs.obs_data_set_default_string(settings, "streaming_output", streaming_output)
	obs.obs_data_set_default_string(settings, "recording_output", recording_output)

	obs.obs_data_set_default_bool(settings, "prompt", prompt)
	obs.obs_data_set_default_int(settings, "key_moment_lead_in", key_moment_lead_in)
	obs.obs_data_set_default_int(settings, "min_key_moment_duration", min_key_moment_duration)
end

function script_description()
	return "Creates a list of 'Key Moment' time-stamps during the event.\nv" .. version
end

function script_update(settings)
	streaming_output = obs.obs_data_get_string(settings, "streaming_output")
	recording_output = obs.obs_data_get_string(settings, "recording_output")
	
	prompt = obs.obs_data_get_bool(settings, "prompt")

	key_moment_lead_in = obs.obs_data_get_int(settings, "key_moment_lead_in")
	min_key_moment_duration = obs.obs_data_get_int(settings, "min_key_moment_duration")

	description = obs.obs_data_get_string(settings, "description")

	key_moment_names = { }
	local key_moment_name_array = obs.obs_data_get_array(settings, "key_moment_names")
	for i=0,obs.obs_data_array_count(key_moment_name_array)-1 do
		local item = obs.obs_data_array_item(key_moment_name_array, i)
		local value = obs.obs_data_get_string(item, "value")
		if not has_value(key_moment_names, value) then
			table.insert(key_moment_names, value)
		end
	end
	obs.obs_data_array_release(key_moment_name_array)

	key_scenes = { }
	local scene_names = obs.obs_frontend_get_scene_names()
	if scene_names ~= nil then
		for _, scene_name in ipairs(scene_names) do
			local key_moment = obs.obs_data_get_string(settings, scene_name)
			key_scenes[scene_name] = key_moment
		end
	end
end

function script_load(settings)
	obs.obs_frontend_add_event_callback(on_event)
end