import bpy
import math
import os
import sys

#rgba
background_color = (0, 0, 0, 1)
green_screen_color = (0, 1, 0, 1)

camera_distance = 3
light_distance_h = 3
light_distance_side = 0.5
light_energy = 1000
ortho_zoom = 2.7
fps = 24
frame_step = 2
light_type = 'POINT'

camera_front = (0, -1*camera_distance, camera_distance)
camera_back = (0, 1*camera_distance, camera_distance)
camera_left = (-1*camera_distance, 0, camera_distance)
camera_right = (1*camera_distance, 0, camera_distance)

resolution_x = 512
resolution_y = resolution_x

render_speed = 1

sprite_anchor = None
sprite_camera = None
sprite_light = None

check_char = '+ '
x_char = 'X '

front = {
    "angle": "front",
    "camera_position": camera_front
}

back = {
    "angle": "back",
    "camera_position": camera_back
}

left = {
    "angle": "left",
    "camera_position": camera_left
}

right = {
    "angle": "right",
    "camera_position": camera_right
}


def reset_blend():
    for x in bpy.data.meshes:
        bpy.data.meshes.remove(x)
        
    for x in bpy.data.materials:
        bpy.data.materials.remove(x)
        
    for x in bpy.data.textures:
        bpy.data.textures.remove(x)
        
    for x in bpy.data.images:
        bpy.data.images.remove(x)
        
    for x in bpy.data.cameras:
        bpy.data.cameras.remove(x)
    
    for x in bpy.data.lights:
        bpy.data.lights.remove(x)
        
    for x in bpy.data.objects:
        bpy.data.objects.remove(x)
            
def set_background():
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
    bpy.context.scene.use_nodes = False
    bpy.context.scene.render.film_transparent = True
   
def build_transparent_screen():
    tree = bpy.context.scene.node_tree
    for node in tree.nodes:
        tree.nodes.remove(node)
    render_node = tree.nodes.new(type='CompositorNodeRLayers')
    render_node.location = -300,300
    comp_node = tree.nodes.new('CompositorNodeComposite')
    comp_node.location = 300,300
    links = tree.links
    links.new(render_node.outputs[0], comp_node.inputs[0])

def build_green_screen():
    
    tree = bpy.context.scene.node_tree
    #reset state
    for node in tree.nodes:
        tree.nodes.remove(node)

    #add Render layers
    render_node = tree.nodes.new(type='CompositorNodeRLayers')
    render_node.location = -300,300
    
    matte_node = tree.nodes.new(type='CompositorNodeAlphaOver')
    matte_node.location = 0,300
    matte_node.inputs[1].default_value = green_screen_color
    
    # create output node
    comp_node = tree.nodes.new('CompositorNodeComposite')   
    comp_node.location = 300,300
    
    links = tree.links
    links.new(render_node.outputs[0], matte_node.inputs[2])
    links.new(matte_node.outputs[0], comp_node.inputs[0])
    

def build_scene():
    scn = bpy.context.scene
    
    print("add empty")
    sprite_anchor = bpy.data.objects.new(name="Sprite Anchor", object_data=None)
    sprite_anchor.location = (0,0,0)
    sprite_anchor.empty_display_type = 'SPHERE'
    sprite_anchor.empty_display_size = 0.5
    scn.collection.objects.link(sprite_anchor)
    
    print("add camera")
    sprite_camera_data = bpy.data.cameras.new(name="Spritemapping Camera")
    sprite_camera_data.type = 'ORTHO'
    sprite_camera_data.ortho_scale = ortho_zoom
    sprite_camera_data.shift_y = 0.2
    
    
    sprite_camera = bpy.data.objects.new(name="Spritemapping Camera", object_data=sprite_camera_data)
    sprite_camera.location = camera_front
    scn.collection.objects.link(sprite_camera)
    scn.camera = sprite_camera
    
    print("aim camera to anchor")
    sprite_camera_constraint = sprite_camera.constraints.new(type='TRACK_TO')
    sprite_camera_constraint.target = sprite_anchor
    sprite_camera_constraint.track_axis = 'TRACK_NEGATIVE_Z'
    sprite_camera_constraint.up_axis = 'UP_Y'
 
    
    print("add light")
    sprite_light_data = bpy.data.lights.new(name="Spritemapping Light", type=light_type)
    sprite_light_data.energy = light_energy
    
    sprite_light = bpy.data.objects.new(name="Spritemapping Light", object_data=sprite_light_data)
    sprite_light.location = (light_distance_side, 0, light_distance_h)
    scn.collection.objects.link(sprite_light)
    
    print("aim light to anchor")
    sprite_light_constraint = sprite_light.constraints.new(type='TRACK_TO')
    sprite_light_constraint.target = sprite_anchor
    sprite_light_constraint.track_axis = 'TRACK_NEGATIVE_Z'
    sprite_light_constraint.up_axis = 'UP_Y'
    
    return sprite_anchor
    
def import_model(spritemap_info, sprite_anchor):
    filepath = spritemap_info["import_path"]
    scn = bpy.context.scene
    if(os.path.exists(filepath)):
        imported_fbx_object = bpy.ops.import_scene.fbx(
            filepath = filepath
        )
        
        fbx_object = bpy.context.selected_objects[0]
        
        print("Contstrain empty to fbx", fbx_object.name)
        scn.collection.objects.link(fbx_object)
        #sprite_anchor_fbx_constraint = sprite_anchor.constraints.new(type="COPY_LOCATION")
        #sprite_anchor_fbx_constraint.target = fbx_object
    else:
        print("Error:")
        print("filepath" + filepath + "could not be found")  

def render_spritemap_angle(direction, spritemap_info):
    scn = bpy.context.scene
    
    angle = direction["angle"]
    camera_position = direction["camera_position"]
    
    pose = spritemap_info["pose"]
    output_path = spritemap_info["output_path"]
    
    #update camera
    scn.camera.location = camera_position

    #framespeed
    scn.render.frame_map_old = 100
    new_speed = math.ceil(scn.render.frame_map_old/render_speed)
    scn.render.frame_map_new = new_speed
    
    #ascertain keyframe start and end
    keys = get_keyframes(bpy.data.objects)
    
    scn.frame_end =  keys[-1]
    scn.frame_start = keys[0]
    all_frames = range(scn.frame_start, scn.frame_end + 1, 2)
    fn=0
    #for f in [f for f in all_frames if f%frame_step == 0 or f == scn.frame_start or f == scn.frame_end + 1]:
    for f in all_frames:
        write_frame(f, angle, pose, output_path, fn)
        fn=fn+1

def write_frame(frame, angle, pose, output_path, frame_number): 
    scn = bpy.context.scene
    scn.frame_set(frame)
    
    folder_name = output_path
    frame_number = str(frame_number).zfill(4)
    file_name = "{a}_{f}".format(p = pose, a = angle, f = frame_number)
    
    filepath = os.path.normpath(os.path.abspath(folder_name +"/"+ file_name))
    
    scn.render.filepath = filepath
    print('rendering... ' + filepath)
    
    bpy.ops.render.render(write_still = True)
        
def get_keyframes(obj_list):
    keyframes = []
    for obj in obj_list:
        anim = obj.animation_data
        if anim is not None and anim.action is not None:
            for fcu in anim.action.fcurves:
                for keyframe in fcu.keyframe_points:
                    x, y = keyframe.co
                    if x not in keyframes:
                        keyframes.append((math.ceil(x)))
    return keyframes 

def prepare_renderer():
    scn = bpy.context.scene
    #update boundaries
    scn.render.resolution_x = resolution_x
    scn.render.resolution_y = resolution_y

def render_every_angle(spritemap_info):
    render_spritemap_angle(front, spritemap_info)
    render_spritemap_angle(back, spritemap_info)
    render_spritemap_angle(left, spritemap_info)
    render_spritemap_angle(right, spritemap_info)

def print_args_error():
    print('Spritesheet Generator Error:')
    print('You must specify valid input and output directories as arguments')
    print('Example: ')
    print('blender --background --python oblique-spritesheet.py -- "./input-models"  "./output-spritesheets"')

def check_path(path):
    valid = os.path.exists(path) and os.path.isdir(path)
    if(valid):
        print(check_char + "Valid Path " + path)
    else:
        print(x_char + "Invalid Path " + path)  
    return valid

def get_dirs():
    argv = sys.argv
    
    try: 
        argv = argv[argv.index("--") + 1:]
    except:
        print("Error: arguments were malformed")
        print("Did you remember to put the -- after the command?")
        print(argv)
        print_args_error()
        return 0;
    
    if(len(argv) < 2):
        print(len(argv))
        print_args_error()
        return 0;
    
    #Resolve paths
    input_dir = os.path.normpath(os.path.abspath(argv[0]))
    output_dir = os.path.normpath(os.path.abspath(argv[1]))
    if not(check_path(input_dir) and check_path(output_dir)):
        print("Error resolving Paths")
        print_args_error()
        return 0;
    
    return { "input_dir": input_dir, "output_dir": output_dir }

def get_spritemap_creation_list(directory_targets):
    inp = directory_targets["input_dir"]
    outp = directory_targets["output_dir"]
    list = []
    for root, dirs, files in os.walk(inp):
        for name in files:
            pose = os.path.splitext(name)[0]
            extension = os.path.splitext(name)[1]
            output_destination = os.path.join(root, name).replace(inp,outp).replace(extension, '')
            import_path = os.path.join(root, name)
            if(extension == ".fbx"):
                list.append({
                    "pose": pose,
                    "import_path": import_path,
                    "output_path": output_destination
                })
                
    return list       

def set_rendering_performance():
    scn = bpy.context.scene
    scn.eevee.taa_render_samples = 2
    scn.eevee.taa_samples = 1
    scn.eevee.use_taa_reprojection = False
    scn.render.use_simplify = True
    scn.render.simplify_child_particles = 0.1
    scn.render.simplify_child_particles_render = 0.1
    scn.render.simplify_subdivision = 2
    scn.render.simplify_subdivision_render = 2
    scn.render.fps = fps
    #scn.sync_mode = 'FRAME_DROP'
    #scn.frame_step = frame_step

def generate_full_spritemap(spritemap_info):
    set_rendering_performance()
    reset_blend()
    set_background()
    #build_transparent_screen()
    #build_green_screen()
    sprite_anchor = build_scene()
    import_model(spritemap_info, sprite_anchor)
    prepare_renderer()
    render_every_angle(spritemap_info)

def main():
    print('Info: Running Oblique Spritesheet Generator.')
    directory_targets = get_dirs();
    
    if(directory_targets == 0):
        return 0;
    
    spritemap_creation_list = get_spritemap_creation_list(directory_targets)
    
    generate_full_spritemap(spritemap_creation_list[0])
    
    for spritemap_info in spritemap_creation_list:
        generate_full_spritemap(spritemap_info)
    
main()

#In-File Testing Example!
#generate_full_spritemap({
#    "pose": "idle-1",
#    "import_path": "F:\\Blender-Stuff\\mixamo-spritesheet-work\\input-mixamo-animations\\player\\idle-1.fbx",
#    "output_path": "F:\\Blender-Stuff\\mixamo-spritesheet-work\\output-sprites-raw\\player\\idle-1\\"
#})
