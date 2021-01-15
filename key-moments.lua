obs = obslua
description = ""
start_time = 0
prompt = true
mode = ""
key_scenes = { }
key_moments = { }

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

function on_event(event)
	if (event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED and mode == "s") or (event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED and mode == "r") then
		start_time = os.time()
		key_moments = {{}, {description}, {}, {"00:00:00","Opening"}}
	elseif start_time > 0 and ((event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED and mode == "s") or (event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED and mode == "r")) then
		for i, item in ipairs(key_moments) do
			key_moments[i] = table.concat(item, " ")
		end
		print(table.concat(key_moments, "\n"))
		key_moments = { }
		start_time = 0
		if prompt == true then
			user32.MessageBoxA(nil, "Tools->Scripts->Script Log\n\nCopy the Key Moments and paste them into the YouTube video description.", "Key Moments", ffi.C.MB_OK)   -- Call C function 'MessageBoxA' from User32
		end
	elseif event == obs.OBS_FRONTEND_EVENT_SCENE_CHANGED and start_time > 0 then
		local scene = obs.obs_frontend_get_current_scene()
		local scene_name = obs.obs_source_get_name(scene)
		if table.getn(key_moments) > 0 and key_moments[table.maxn(key_moments)][2] ~= scene_name then
			for _, key_scene in ipairs(key_scenes) do
				if scene_name == key_scene then
					local delta = os.difftime(os.time() - 2, start_time)
					
					local hh = math.floor(delta / 60 / 60)
					local mm = math.floor(delta / 60) % 60
					local ss = delta % 60
					
					local timestamp = string.format("%02d:%02d:%02d", hh, mm, ss)
					
					table.insert(key_moments, {timestamp, scene_name})
					break
				end
			end
		end
	end
end

function script_properties()
	local props = obs.obs_properties_create()

	local m = obs.obs_properties_add_list(props, "mode", "Mode", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_list_add_string(m, "Recording", "r")
	obs.obs_property_list_add_string(m, "Streaming", "s")
	obs.obs_property_list_add_string(m, "Off", "")	

	obs.obs_properties_add_bool(props, "prompt", "Display Prompts")

	obs.obs_properties_add_text(props, "description", "Video Description", obs.OBS_TEXT_MULTILINE)

	local grp = obs.obs_properties_create()
	local scenes = obs.obs_frontend_get_scenes()
	if scenes ~= nil then
		for _, scene in ipairs(scenes) do
			local name = obs.obs_source_get_name(scene);
			obs.obs_properties_add_bool(grp, name, name)
		end
	end
	obs.source_list_release(scenes)
	obs.obs_properties_add_group(props, "key_scenes", "Key Scenes", obs.OBS_GROUP_NORMAL, grp)

	return props
end

function script_defaults(settings)
	obs.obs_data_set_default_bool(settings, "prompt", true)
end

function script_description()
	return "Creates a list of 'Key Moment' time-stamps during the event.\n\nMade by Andrew Carbert"
end

function script_update(settings)
	mode = obs.obs_data_get_string(settings, "mode")
	
	prompt = obs.obs_data_get_bool(settings, "prompt")

	description = obs.obs_data_get_string(settings, "description")

	local scenes = obs.obs_frontend_get_scenes()
	if scenes ~= nil then
		for _, scene in ipairs(scenes) do
			local name = obs.obs_source_get_name(scene);
			local checked = obs.obs_data_get_bool(settings, name)
			if checked then
				table.insert(key_scenes, name)
			end
		end
	end
	obs.source_list_release(scenes)
end

function script_load(settings)
	obs.obs_frontend_add_event_callback(on_event)
end
