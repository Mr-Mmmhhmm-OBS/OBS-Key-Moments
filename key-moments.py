import obspython as obs
import time
import math
import pyperclip as clipboard

version=1.2

streaming_output_options = [ "--Disabled--", "Console" ] # , "YouTube"
streaming_output = streaming_output_options[1]
streaming = None

recording_output_options = [ "--Disabled--", "Console" ] # , "File"
recording_output = recording_output_options[1]
recording = None
copy_to_clipboard_options = ["--Disabled--", "Streamed Moments", "Recorded Moments"]
copy_to_clipboard = copy_to_clipboard_options[0]
key_moment_lead_in = 2
min_key_moment_duration = 60

description = ""
key_moment_names = []
key_scenes = { }

def compile_key_momemnts(obj):
	# Remove duplicate key-moments
	for i, item in enumerate(obj['key_moments']):
		if len(item) == 2 and len(obj['key_moments'][i-1]) == 2 and obj['key_moments'][i-1][1] == item[1]:
			del obj['key_moments'][i]
	
	# Turn each key-moment into a string
	for i, item in enumerate(obj['key_moments']):
		if len(item) == 2:
			delta = item[0]
			if item[0] > key_moment_lead_in:
				delta = item[0] - key_moment_lead_in

			hh = math.floor(delta / 60 / 60)
			mm = math.floor(delta / 60 % 60)
			ss = math.floor(delta % 60)

			obj['key_moments'][i] = "{:02}:{:02}:{:02} {}".format(hh, mm, ss, item[1])
		elif len(item) == 1:
			obj['key_moments'][i] = item[0]
		else:
			obj['key_moments'][i] = ""
	return "\n".join(obj['key_moments'])

def update_key_moments(obj, scene_name):
	if len(obj['key_moments']) > 0 and key_scenes[scene_name] != "" and obj['key_moments'][len(obj['key_moments'])-1][1] != key_scenes[scene_name]:
		for key_scene, key_moment in key_scenes.items():
			if scene_name == key_scene:
				timestamp = time.time() - obj['start_time']
				if timestamp - obj['key_moments'][len(obj['key_moments'])-1][0] < min_key_moment_duration:
					# Update previous 'key moment' to this scene name
					obj['key_moments'][len(obj['key_moments'])-1][1] = key_moment
				else:
					# Insert new 'key moment'
					obj['key_moments'].append([ timestamp, key_moment ])
				break

def on_event(event):
	global streaming
	global recording
	if event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED and streaming_output != streaming_output_options[0]:
		streaming = { 'start_time': time.time(), 'key_moments': [ [], [ description ], [], [ 0, key_moment_names[0] ] ] }
	elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED and recording_output != recording_output_options[0]:
		recording = { 'start_time': time.time(), 'key_moments': [ [], [ description ], [], [ 0, key_moment_names[0] ] ] }
	elif event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED and streaming != None:
		print("\nStreaming Key Moments")
		message = compile_key_momemnts(streaming)
		print(message)
		streaming = None
		if copy_to_clipboard == copy_to_clipboard_options[1]:
			clipboard.copy(message)
	elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED and recording != None:
		print("\nRecording Key Moments")
		message = compile_key_momemnts(recording)
		print(message)
		clipboard.copy(message)
		recording = None
		if copy_to_clipboard == copy_to_clipboard_options[2]:
			clipboard.copy(message)
	elif event == obs.OBS_FRONTEND_EVENT_SCENE_CHANGED and (streaming != None or recording != None):
		scene = obs.obs_frontend_get_current_scene()
		scene_name = obs.obs_source_get_name(scene)
		if streaming != None:
			update_key_moments(streaming, scene_name)
		if recording != None:
			update_key_moments(recording, scene_name)

def has_value (tab, val):
    for value in tab:
        if value == val:
            return True

    return False

def key_moment_names_modified(props, property, settings):
	scene_names = obs.obs_frontend_get_scene_names()
	if scene_names != None:
		for scene_name in scene_names:
			p = obs.obs_properties_get(props, scene_name)
			add_key_moment_list(p, False)
	return True

def add_key_moment_list(p, required):
	obs.obs_property_list_clear(p)
	if not required:
		obs.obs_property_list_add_string(p, "", "")
	for key_moment_name in key_moment_names:
		obs.obs_property_list_add_string(p, key_moment_name, key_moment_name)

def on_property_modified(props, property, settings):
	has_output = streaming_output != streaming_output_options[0] or recording_output != recording_output_options[0]
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "copy_to_clipboard"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_moment_lead_in"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "min_key_moment_duration"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "description"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_moment_names"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_scenes"), has_output)
	return True

def script_properties():
	has_output = streaming_output != streaming_output_options[0] or recording_output != recording_output_options[0]
	props = obs.obs_properties_create()

	p = obs.obs_properties_add_list(props, "streaming_output", "Streaming Output", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, on_property_modified)
	for option in streaming_output_options:
		obs.obs_property_list_add_string(p, option, option)

	p = obs.obs_properties_add_list(props, "recording_output", "Recording Output", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, on_property_modified)
	for option in recording_output_options:
		obs.obs_property_list_add_string(p, option, option)

	p = obs.obs_properties_add_list(props, "copy_to_clipboard", "Copy To Clipboard", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_enabled(p, has_output)
	for option in copy_to_clipboard_options:
		obs.obs_property_list_add_string(p, option, option)

	p = obs.obs_properties_add_int_slider(props, "key_moment_lead_in", "Key Moment Lead In", 0, 10, 1)
	obs.obs_property_set_enabled(p, has_output)

	p = obs.obs_properties_add_int_slider(props, "min_key_moment_duration", "Min Key-Moment Duration", 1, 300, 10)
	obs.obs_property_set_enabled(p, has_output)

	p = obs.obs_properties_add_text(props, "description", "Video Description", obs.OBS_TEXT_MULTILINE)
	obs.obs_property_set_enabled(p, has_output)

	p = obs.obs_properties_add_editable_list(props, "key_moment_names", "Key Moments", obs.OBS_EDITABLE_LIST_TYPE_STRINGS, None, None)
	obs.obs_property_set_enabled(p, has_output)
	obs.obs_property_set_modified_callback(p, key_moment_names_modified)

	grp = obs.obs_properties_create()
	scene_names = obs.obs_frontend_get_scene_names()
	if scene_names != None:
		for scene_name in scene_names:
			p = obs.obs_properties_add_list(grp, scene_name, scene_name, obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
			obs.obs_property_set_enabled(p, has_output)
			add_key_moment_list(p, False)
	obs.obs_properties_add_group(props, "key_scenes", "Key Scenes", obs.OBS_GROUP_NORMAL, grp)

	return props

def script_defaults(settings):
	obs.obs_data_set_default_string(settings, "streaming_output", streaming_output)
	obs.obs_data_set_default_string(settings, "recording_output", recording_output)

	obs.obs_data_set_default_string(settings, "copy_to_clipboard", copy_to_clipboard)
	obs.obs_data_set_default_int(settings, "key_moment_lead_in", key_moment_lead_in)
	obs.obs_data_set_default_int(settings, "min_key_moment_duration", min_key_moment_duration)

def script_description():
	return "Creates a list of 'Key Moment' time-stamps during the event.\nv" + str(version)

def script_update(settings):
	global streaming_output
	streaming_output = obs.obs_data_get_string(settings, "streaming_output")
	global recording_output
	recording_output = obs.obs_data_get_string(settings, "recording_output")
	
	global copy_to_clipboard
	copy_to_clipboard = obs.obs_data_get_string(settings, "copy_to_clipboard")

	global key_moment_lead_in
	key_moment_lead_in = obs.obs_data_get_int(settings, "key_moment_lead_in")
	global min_key_moment_duration
	min_key_moment_duration = obs.obs_data_get_int(settings, "min_key_moment_duration")

	global description
	description = obs.obs_data_get_string(settings, "description")

	global key_moment_names 
	key_moment_names = []

	global key_moment_name_array
	key_moment_name_array = obs.obs_data_get_array(settings, "key_moment_names")
	for i in range(obs.obs_data_array_count(key_moment_name_array)):
		item = obs.obs_data_array_item(key_moment_name_array, i)
		value = obs.obs_data_get_string(item, "value")
		if not has_value(key_moment_names, value):
			key_moment_names.append(value)
	obs.obs_data_array_release(key_moment_name_array)

	global key_scenes
	key_scenes = { }
	global scene_names
	scene_names = obs.obs_frontend_get_scene_names()
	if scene_names != None:
		for scene_name in scene_names:
			key_moment = obs.obs_data_get_string(settings, scene_name)
			key_scenes[scene_name] = key_moment

def script_load(settings):
	obs.obs_frontend_add_event_callback(on_event)