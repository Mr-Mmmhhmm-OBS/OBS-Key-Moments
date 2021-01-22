import obspython as obs
import time
import math
from datetime import datetime
import pyperclip as clipboard
from win10toast import ToastNotifier
toaster = ToastNotifier()

# -*- coding: utf-8 -*-
# Sample Python code for youtube.liveStreams.update
# See instructions for running these code samples locally:
# https://developers.google.com/explorer-help/guides/code_samples#python
import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

scopes = ["https://www.googleapis.com/auth/youtube"]

version=2.1

OUTPUT_OPTION_CLIPBOARD = "Copy To Clipboard"
OUTPUT_OPTION_CONSOLE = "Console"
OUTPUT_OPTION_FILE = "Save To File"

YOUTUBE_DEVELOPER_KEY = "99730038784-1esj3gnhrebbldietubd6hdcklss9aqf.apps.googleusercontent.com"

streaming_output = ( {"name":OUTPUT_OPTION_CLIPBOARD, "value":True }, {"name":OUTPUT_OPTION_CONSOLE, "value":True }, {"name":OUTPUT_OPTION_FILE, "value":True }, )
streaming = None

recording_output = ( { "name":OUTPUT_OPTION_CLIPBOARD, "value":False }, { "name":OUTPUT_OPTION_CONSOLE, "value":True }, {"name":OUTPUT_OPTION_FILE, "value":True }, ) # , "File"
recording = None

file_folder = None
file_name = "%Y/%b %d"

key_moment_lead_in = 2
min_key_moment_duration = 60

description = ""
key_moment_names = [ "Opening", "Closing" ]
key_scenes = { }

def make_toast(message):
	toaster.show_toast("OBS Key Moments", message, duration=10, threaded=True, icon_path=script_path()+"/obs-icon-small.ico")

def save_to_file(message):
	if file_folder != None and len(file_name) > 0:
		path = file_folder + "/" + datetime.now().strftime(file_name) + ".txt"
		if not os.path.exists(os.path.dirname(path)):
			try:
				os.makedirs(os.path.dirname(path))
			except OSError as exc: # Guard against race condition
				if exc.errno != errno.EEXIST:
					raise
		with open(path, "a+") as f:
			f.write("\n" + type + " Key Moments---------------\n" + message)
	else:
		print("Invalid Save Location!")

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

			obj['key_moments'][i] = "{:02d}:{:02d}:{:02d} {}".format(hh, mm, ss, item[1])
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

def execute_output(output_options, type, message):
	for option in output_options:
		if option['value']:
			if option['name'] == OUTPUT_OPTION_CLIPBOARD:
				clipboard.copy(message)
				make_toast("The key-moments from your " + type.lower() + " have been copied to your clipboard.")
			if option['name'] == OUTPUT_OPTION_CONSOLE:
				print("\n" + type + " Key Moments\n")
				print(message)
			if option['name'] == OUTPUT_OPTION_FILE:
				save_to_file(message)
				
def on_event(event):
	global streaming
	global recording
	if event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED and get_has_output(streaming_output):
		if len(key_moment_names) == 0:
			make_toast("Warning!\n\nYou cannot record key-moments without items in the key moment name list!")
		else:
			streaming = { 'start_time': time.time(), 'key_moments': [ [ description ], [], [ 0, key_moment_names[0] ] ] }
	elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED and get_has_output(recording_output):
		if len(key_moment_names) == 0:
			make_toast("Warning!\n\nYou cannot record key-moments without items in the key moment name list!")
		else:		
			recording = { 'start_time': time.time(), 'key_moments': [ [ description ], [], [ 0, key_moment_names[0] ] ] }
	elif event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED and streaming != None:
		message = compile_key_momemnts(streaming)
		execute_output(streaming_output, "Streaming", message)
		streaming = None
	elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED and recording != None:
		message = compile_key_momemnts(recording)
		execute_output(recording_output, "Recording", message)
		recording = None
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

def get_has_output(options):
	for option in options:
		if option['value'] == True:
			return True
	return False

def on_property_modified(props, property, settings):
	has_output = get_has_output(streaming_output) or get_has_output(recording_output)
	# TODO: Code proper exclusivity
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "recording_output_0"), not streaming_output[0]['value'])
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "streaming_output_0"), not recording_output[0]['value'])

	obs.obs_property_set_visible(obs.obs_properties_get(props, "file_folder"), streaming_output[2]['value'] or recording_output[2]['value'])
	obs.obs_property_set_visible(obs.obs_properties_get(props, "file_name"), streaming_output[2]['value'] or recording_output[2]['value'])
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_moment_lead_in"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "min_key_moment_duration"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "description"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_moment_names"), has_output)
	obs.obs_property_set_enabled(obs.obs_properties_get(props, "key_scenes"), has_output)
	return True

def script_properties():
	has_output = get_has_output(streaming_output) or get_has_output(recording_output)
	props = obs.obs_properties_create()

	group = obs.obs_properties_create()
	for i, option in enumerate(streaming_output):
		p = obs.obs_properties_add_bool(group, 'streaming_output_' + str(i), option['name'])
		obs.obs_property_set_modified_callback(p, on_property_modified)
	obs.obs_properties_add_group(props, "streaming_output", "Streaming Output", obs.OBS_GROUP_NORMAL, group)

	group = obs.obs_properties_create()
	for i, option in enumerate(recording_output):
		p = obs.obs_properties_add_bool(group, 'recording_output_' + str(i), option['name'])
		obs.obs_property_set_modified_callback(p, on_property_modified)
	obs.obs_properties_add_group(props, "recording_output", "Recording Output", obs.OBS_GROUP_NORMAL, group)

	p = obs.obs_properties_add_path(props, "file_folder", "File Folder", obs.OBS_PATH_DIRECTORY, None, None)
	obs.obs_property_set_visible(p, streaming_output[2]['value'] or recording_output[2]['value'])

	p = obs.obs_properties_add_text(props, "file_name", "File Name", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_visible(p, streaming_output[2]['value'] or recording_output[2]['value'])

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
		for scene_name in scene_names:
			p = obs.obs_properties_add_list(grp, scene_name, scene_name, obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
			obs.obs_property_set_enabled(p, has_output)
			add_key_moment_list(p, False)
	obs.obs_properties_add_group(props, "key_scenes", "Key Scenes", obs.OBS_GROUP_NORMAL, grp)

	p = obs.obs_properties_add_text(props, "description", "Video Description", obs.OBS_TEXT_MULTILINE)
	obs.obs_property_set_enabled(p, has_output)

	return props

def script_defaults(settings):
	for i, option in enumerate(streaming_output):
		obs.obs_data_set_default_bool(settings, "streaming_output_" + str(i), option['value'])

	for i, option in enumerate(recording_output):
		obs.obs_data_set_default_bool(settings, "recording_output_" + str(i), option['value'])
	
	obs.obs_data_set_default_string(settings, "file_name", file_name)
	
	obs.obs_data_set_default_int(settings, "key_moment_lead_in", key_moment_lead_in)
	obs.obs_data_set_default_int(settings, "min_key_moment_duration", min_key_moment_duration)

def script_description():
	return "Creates a list of 'Key Moment' time-stamps during the event.\nv" + str(version)

def script_update(settings):
	global streaming_output
	for i, option in enumerate(streaming_output):
		streaming_output[i]['value'] = obs.obs_data_get_bool(settings, "streaming_output_" + str(i))

	global recording_output
	for i, option in enumerate(recording_output):
		recording_output[i]['value'] = obs.obs_data_get_bool(settings, "recording_output_" + str(i))

	global file_folder
	file_folder = obs.obs_data_get_string(settings, "file_folder")

	global file_name
	file_name = obs.obs_data_get_string(settings, "file_name")

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