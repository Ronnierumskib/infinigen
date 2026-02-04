import bpy
import sys
import os


# road placement in RoadWrap.blend
argv = sys.argv[sys.argv.index("--") + 1:]
scene_filepath = argv[0]

road_x = 0 
road_y = 21 

#bpy.ops.wm.open_mainfile(filepath="/home/cmo/infinigen_original/outputs/Terrains/test_terrain_pop/scene.blend")
bpy.ops.wm.open_mainfile(filepath=scene_filepath)

# -----------------------
# Locate terrain
# -----------------------
terrain = None
for obj in bpy.data.objects: # If fine_terrain was run, we need OpaqueTerrain_fine
    if obj.type == 'MESH' and "opaqueterrain_fine" in obj.name.lower():
        terrain = obj
        break

# Else, we get normal opaque terrain
if not terrain:
    for obj in bpy.data.objects: # If fine_terrain was run, we need OpaqueTerrain_fine
        if obj.type == 'MESH' and "opaqueterrain" in obj.name.lower():
            terrain = obj
            break
    
if terrain is None:
    raise RuntimeError("Terrain not found")

# -----------------------
# Append road asset and set modifiers
# -----------------------
road_blend = "/home/cmo/infinigen_original/RoadWrap.blend"
with bpy.data.libraries.load(road_blend, link=False) as (data_from, data_to):
    data_to.objects = [name for name in data_from.objects if "Road" in name]

road = data_to.objects[0]
bpy.context.collection.objects.link(road)

for mod in road.modifiers:
    if mod.type == 'NODES':
        road_mod = mod
        break
road_mod["Socket_2"] = 5 # Blur Iterations
road_mod["Socket_3"] = -0.15 # Z offset

# -----------------------
# Fix road image texture paths
# -----------------------

texture_base_path = "/home/cmo/infinigen_original/"  # Adjust this to where your textures are

for img in bpy.data.images:
    if img.filepath and not os.path.exists(bpy.path.abspath(img.filepath)):
        # Get just the filename
        filename = os.path.basename(img.filepath)
        
        # Try to find the texture in common locations
        possible_paths = [
            os.path.join(texture_base_path, filename),
            os.path.join(texture_base_path, "textures", filename),
            os.path.join(os.path.dirname(road_blend), filename),
            os.path.join(os.path.dirname(road_blend), "textures", filename),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                img.filepath = path
                img.reload()
                print(f"Fixed texture path for {img.name}: {path}")
                break
        else:
            print(f"Warning: Could not find texture file: {filename}")


# -----------------------
# Place road
# -----------------------
road.location = (0, 0, 2)

bpy.context.view_layer.objects.active = road
road.select_set(True)

# Apply transforms
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# -----------------------
# Hook terrain geometry info into road GN
# -----------------------
gn_mod = None
for mod in road.modifiers:
    if mod.type == 'NODES':
        gn_mod = mod
        break

if gn_mod is None:
    raise RuntimeError("Road has no GN modifier")

node_group = gn_mod.node_group

for node in node_group.nodes:
    if node.type == 'OBJECT_INFO':
        node.inputs[0].default_value = terrain

# -----------------------
# Append terrain smoothing GN group to generated terrain
# -----------------------

with bpy.data.libraries.load(road_blend, link=False) as (src, dst):
    dst.node_groups = ["TerrainSmoothing"]

gn = bpy.data.node_groups["TerrainSmoothing"]

mod = terrain.modifiers.new("RoadFlatten", "NODES")
mod.node_group = gn

for node in mod.node_group.nodes:
    if node.type == 'GROUP_INPUT':
        continue
# Set inputs
mod["Socket_2"] = (road_x, road_y, 0.0)  # Road Center
mod["Socket_3"] = 6.5              # Width
mod["Socket_4"] = 47.5*3             # Length
mod["Socket_5"] = 4.0              # Falloff
mod["Socket_6"] = 0.8              # Strength

# save as an overwrite:
bpy.ops.wm.save_mainfile()

#bpy.ops.wm.save_as_mainfile(filepath="/home/cmo/infinigen_original/outputs/Terrains/test_terrain_pop/scene_road.blend")
print("Road successfully applied")