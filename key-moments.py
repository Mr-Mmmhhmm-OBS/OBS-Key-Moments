import obspython as obs
import os
import time
import math
from datetime import datetime
import pyperclip as clipboard
from win10toast import ToastNotifier
toaster = ToastNotifier()
import webbrowser

version="2.9"

OUTPUT_OPTION_CLIPBOARD = "copy_to_clipboard"
OUTPUT_OPTION_CONSOLE = "write_to_console"
OUTPUT_OPTION_FILE = "save_to_file"

streaming_output = { OUTPUT_OPTION_CLIPBOARD:{ "name":"Copy To Clipboard", "value":True, 'exclusive':True }, OUTPUT_OPTION_CONSOLE:{ "name": "Write To Console", "value":True }, OUTPUT_OPTION_FILE:{ "name": "Save To File", "value":True }, }
channel_id = ""
streaming = None

recording_output = { OUTPUT_OPTION_CLIPBOARD:{ "name":"Copy To Clipboard", "value":False, 'exclusive':True }, OUTPUT_OPTION_CONSOLE:{ "name": "Write To Console", "value":True }, OUTPUT_OPTION_FILE:{ "name": "Save To File", "value":True }, }
recording = None

file_folder = None
file_name = "%Y/%b %d"

key_moment_lead_in = 2
min_key_moment_duration = 60

key_moment_names = [ ]
key_scenes = { }

def make_toast(message):
	toaster.show_toast("OBS Key Moments", message, duration=10, threaded=True, icon_path=script_path()+"/obs-icon-small.ico")

def save_to_file(output_type, message):
	if file_folder != None and len(file_name) > 0:
		path = file_folder + "/" + datetime.now().strftime(file_name) + ".txt"
		if not os.path.exists(os.path.dirname(path)):
			try:
				os.makedirs(os.path.dirname(path))
			except OSError as exc: # Guard against race condition
				if exc.errno != errno.EEXIST:
					raise
		with open(path, "a+") as f:
			f.write("\n" + output_type + " Key Moments\n" + message)
	else:
		raise Exception("Invalid Save Location!")

def compile_key_momemnts(key_moments):
	print(str(key_scenes))
	print(str(key_moments))

	# Remove duplicate key-moments
	for i, item in enumerate(key_moments):
		if key_moments[i-1][1] == item[1]:
			del key_moments[i]
	
	# Turn each key-moment into a string
	for i, item in enumerate(key_moments):
		delta = item[0]
		if item[0] > key_moment_lead_in:
			delta = item[0] - key_moment_lead_in

		hh = math.floor(delta / 60 / 60)
		mm = math.floor(delta / 60 % 60)
		ss = math.floor(delta % 60)

		key_moments[i] = "{:02d}:{:02d}:{:02d} {}".format(hh, mm, ss, item[1])
	return "\n".join(key_moments)

def update_key_moments(obj, scene_name):
	if key_scenes[scene_name] != "" and obj['key_moments'][len(obj['key_moments'])-1][1] != key_scenes[scene_name]:
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

def execute_output(output_options, output_type, message):
	for option in output_options:
		if output_options[option]['value']:
			if option == OUTPUT_OPTION_CLIPBOARD:
				clipboard.copy(message)
				make_toast("The key-moments from your " + output_type.lower() + " have been copied to your clipboard.")
			elif option == OUTPUT_OPTION_CONSOLE:
				print("\n" + output_type + " Key Moments\n" + message)
			elif option == OUTPUT_OPTION_FILE:
				save_to_file(output_type, message)
				
def on_event(event):
	global streaming
	global recording

	if event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED and get_has_output(streaming_output):
		if len(key_moment_names) == 0:
			raise Exception("You cannot record key-moments without items in the key moment name list!")
		else:
			streaming = { 'start_time': time.time(), 'key_moments': [ [ 0, key_moment_names[0] ] ] }
	elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED and get_has_output(recording_output):
		if len(key_moment_names) == 0:
			raise Exception("You cannot record key-moments without items in the key moment name list!")
		else:		
			recording = { 'start_time': time.time(), 'key_moments': [ [ 0, key_moment_names[0] ] ] }
	elif event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED and streaming != None:
		message = compile_key_momemnts(streaming['key_moments'])
		execute_output(streaming_output, "Streaming", message)
		if channel_id != "":
			webbrowser.open("https://studio.youtube.com/channel/"+channel_id+"/videos/live")
		streaming = None
	elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED and recording != None:
		message = compile_key_momemnts(recording['key_moments'])
		execute_output(recording_output, "Recording", message)
		recording = None
	elif event == obs.OBS_FRONTEND_EVENT_SCENE_CHANGED and (streaming != None or recording != None):
		scene = obs.obs_frontend_get_current_scene()
		scene_name = obs.obs_source_get_name(scene)
		obs.obs_source_release(scene)
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
			add_key_moment_list(p)
	return True

def add_key_moment_list(p):
	obs.obs_property_list_clear(p)
	obs.obs_property_list_add_string(p, "", "")
	for key_moment_name in key_moment_names:
		obs.obs_property_list_add_string(p, key_moment_name, key_moment_name)

def get_has_output(options):
	for option in options:
		if options[option]['value'] == True:
			return True
	return False

def on_property_modified(props, property, settings):
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "recording_output_" + OUTPUT_OPTION_CLIPBOARD), not streaming_output[OUTPUT_OPTION_CLIPBOARD]['value'])
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "streaming_output_" + OUTPUT_OPTION_CLIPBOARD), not recording_output[OUTPUT_OPTION_CLIPBOARD]['value'])
	has_output = get_has_output(streaming_output) or get_has_output(recording_output)
	
	obs.obs_property_set_visible(obs.obs_properties_get(props, "file_folder"), streaming_output[OUTPUT_OPTION_FILE]['value'] or recording_output[OUTPUT_OPTION_FILE]['value'])
	obs.obs_property_set_visible(obs.obs_properties_get(props, "file_name"), streaming_output[OUTPUT_OPTION_FILE]['value'] or recording_output[OUTPUT_OPTION_FILE]['value'])
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_moment_lead_in"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "min_key_moment_duration"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_moment_names"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_scenes"), has_output)
	return True

def script_properties():
	has_output = get_has_output(streaming_output) or get_has_output(recording_output)
	props = obs.obs_properties_create()

	group = obs.obs_properties_create()
	for key in streaming_output:
		p = obs.obs_properties_add_bool(group, 'streaming_output_' + str(key), streaming_output[key]['name'])
		obs.obs_property_set_modified_callback(p, on_property_modified)
	obs.obs_properties_add_text(group, "channel_id", "Channel ID", obs.OBS_TEXT_DEFAULT)
	obs.obs_properties_add_group(props, "streaming_output", "Streaming Output", obs.OBS_GROUP_NORMAL, group)

	group = obs.obs_properties_create()
	for key in recording_output:
		p = obs.obs_properties_add_bool(group, 'recording_output_' + str(key), recording_output[key]['name'])
		obs.obs_property_set_modified_callback(p, on_property_modified)
	obs.obs_properties_add_group(props, "recording_output", "Recording Output", obs.OBS_GROUP_NORMAL, group)

	obs.obs_property_set_enabled(obs.obs_properties_get(props, "recording_output_" + OUTPUT_OPTION_CLIPBOARD), not streaming_output[OUTPUT_OPTION_CLIPBOARD]['value'])
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "streaming_output_" + OUTPUT_OPTION_CLIPBOARD), not recording_output[OUTPUT_OPTION_CLIPBOARD]['value'])
	

	p = obs.obs_properties_add_path(props, "file_folder", "File Folder", obs.OBS_PATH_DIRECTORY, None, None)
	obs.obs_property_set_visible(p, streaming_output[OUTPUT_OPTION_FILE]['value'] or recording_output[OUTPUT_OPTION_FILE]['value'])

	p = obs.obs_properties_add_text(props, "file_name", "File Name", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_visible(p, streaming_output[OUTPUT_OPTION_FILE]['value'] or recording_output[OUTPUT_OPTION_FILE]['value'])

	p = obs.obs_properties_add_int_slider(props, "key_moment_lead_in", "Key Moment Lead In", 0, 10, 1)
	obs.obs_property_set_enabled(p, has_output)

	p = obs.obs_properties_add_int_slider(props, "min_key_moment_duration", "Min Key-Moment Duration", 1, 300, 10)
	obs.obs_property_set_enabled(p, has_output)

	p = obs.obs_properties_add_editable_list(props, "key_moment_names", "Key Moments", obs.OBS_EDITABLE_LIST_TYPE_STRINGS, None, None)
	obs.obs_property_set_enabled(p, has_output)
	obs.obs_property_set_modified_callback(p, key_moment_names_modified)

	grp = obs.obs_properties_create()
	scene_names = obs.obs_frontend_get_scene_names()
	if scene_names != None:
		for i, scene_name in enumerate(scene_names):
			p = obs.obs_properties_add_list(grp, "scene-" + scene_name, scene_name, obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
			obs.obs_property_set_enabled(p, has_output)
			add_key_moment_list(p)
	obs.obs_properties_add_group(props, "key_scenes", "Key Scenes", obs.OBS_GROUP_NORMAL, grp)

	return props

def script_defaults(settings):
	for key in streaming_output:
		obs.obs_data_set_default_bool(settings, "streaming_output_" + str(key), streaming_output[key]['value'])

	for key in recording_output:
		obs.obs_data_set_default_bool(settings, "recording_output_" + str(key), recording_output[key]['value'])
	
	obs.obs_data_set_default_string(settings, "file_name", file_name)
	
	obs.obs_data_set_default_int(settings, "key_moment_lead_in", key_moment_lead_in)
	obs.obs_data_set_default_int(settings, "min_key_moment_duration", min_key_moment_duration)

def script_description():
	return "Creates a list of 'Key Moment' time-stamps during the event.\nhttps://github.com/Mr-Mmhhmm-OBS/OBS-Key-Moments\nv" + version

def script_update(settings):
	global streaming_output
	for key in streaming_output:
		streaming_output[key]['value'] = obs.obs_data_get_bool(settings, "streaming_output_" + str(key))
	
	global channel_id
	channel_id = obs.obs_data_get_string(settings, "channel_id")

	global recording_output
	for key in recording_output:
		recording_output[key]['value'] = obs.obs_data_get_bool(settings, "recording_output_" + str(key))

	global file_folder
	file_folder = obs.obs_data_get_string(settings, "file_folder")

	global file_name
	file_name = obs.obs_data_get_string(settings, "file_name")

	global key_moment_lead_in
	key_moment_lead_in = obs.obs_data_get_int(settings, "key_moment_lead_in")
	global min_key_moment_duration
	min_key_moment_duration = obs.obs_data_get_int(settings, "min_key_moment_duration")

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
	scene_name_array = obs.obs_data_get_array(settings, "scene_names")
	if scene_name_array != None:
		for i in range(obs.obs_data_array_count(scene_name_array)):
			data_item = obs.obs_data_array_item(scene_name_array, i)
			scene_name = obs.obs_data_get_string(data_item, "scene_name")
			key_moment = obs.obs_data_get_string(settings, "scene-" + scene_name)
			key_scenes[scene_name] = key_moment
		obs.obs_data_array_release(scene_name_array)

def script_save(settings):
	scene_names = obs.obs_frontend_get_scene_names()
	if scene_names != None:
		# Update scenename list
		array = obs.obs_data_array_create()
		for i, scene_name in enumerate(scene_names):
			data_item = obs.obs_data_create()
			obs.obs_data_set_string(data_item, "scene_name", scene_name)
			obs.obs_data_array_insert(array, i, data_item)
		obs.obs_data_set_array(settings, "scene_names", array)

def script_load(settings):
	obs.obs_frontend_add_event_callback(on_event)