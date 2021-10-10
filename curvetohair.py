import bpy
import math
import mathutils
from math import radians
from array import array

def main(context):
	#get selected object
	curve_object = bpy.context.active_object
	#check that it is a curve
	if curve_object.type != 'CURVE':
		return
	
	curve_data = curve_object.data
	
	#check bevel mode. profile is not supported (yet:tm:)
	if curve_data.bevel_mode == 'PROFILE':
		#todo: support profile mode
		return
	
	#make sure the curve actually has a bevel object
	if curve_data.bevel_mode == 'OBJECT' and curve_data.bevel_object == None:
		return
	
	spline = curve_data.splines[0]
	spline_points = None
	
	#points are different depending on if the curve is a NURBS or bezier curve
	if spline.type == 'BEZIER':
		spline_points = spline.bezier_points
	elif spline.type == 'NURBS':
		spline_points = spline.points
	else:
		return
	
	#flip spline tilt
	#note: for some reason, spline tilt twists hair in the opposite direction from what you'd expect
	#this is the only way I can think to fix the issue :(
	for spline_point in spline_points:
			spline_point.tilt = -spline_point.tilt
		
	#calculate rotation of the hair emitter
	hair_emitter_normal = mathutils.Vector(spline_points[0].co.xyz - spline_points[1].co.xyz).normalized()
	hair_emitter_rotation = hair_emitter_normal.to_track_quat('Z', 'Y')
	
	#make curve wireframe in viewport
	curve_object.display_type = 'WIRE'
	curve_object.hide_render = True
	#hide in cycles viewport
	curve_object.cycles_visibility.camera = False
	curve_object.cycles_visibility.diffuse = False
	curve_object.cycles_visibility.glossy = False
	curve_object.cycles_visibility.transmission = False
	curve_object.cycles_visibility.scatter = False
	curve_object.cycles_visibility.shadow = False
	
	#add a hair guide forcefield to the curve (currently the active object)
	curve_object.field.type = 'GUIDE'
	curve_object.field.guide_minimum = 0
	
	#create a collection for the field to influence and add the curve to it 
	field_collection = bpy.context.blend_data.collections.new(name='curve to hair influence col')
	field_collection.objects.link(curve_object)
	field_collection.use_fake_user = True
	
	hair_emitter = None
		
	#todo: avoid using bpy.ops
	if(curve_data.bevel_mode == 'ROUND'):	
		#create circle with radius of round bevel curve
		bpy.ops.mesh.primitive_circle_add(fill_type='TRIFAN', radius = curve_data.bevel_depth, rotation = hair_emitter_rotation.to_euler(), location = (0, 0, 0))
		#the newly created circle is selected, so grab it from context
		hair_emitter = bpy.context.active_object
		
	elif(curve_data.bevel_mode == 'OBJECT'):
		#create a new mesh with the shape of the bevel object
		
		#select the bevel object
		bpy.ops.object.select_all(action='DESELECT')
		bpy.context.view_layer.objects.active = curve_data.bevel_object
		curve_data.bevel_object.select_set(True)
		#duplicate and convert copy to mesh
		bpy.ops.object.duplicate_move()
		hair_emitter = bpy.context.active_object
		bpy.ops.object.convert(target='MESH')
		bpy.ops.object.editmode_toggle()
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.edge_face_add()
		bpy.ops.object.editmode_toggle()
		
	#orient emitter
	hair_emitter.parent = curve_object
	hair_emitter.rotation_euler = hair_emitter_rotation.to_euler()
	hair_emitter.rotation_euler.rotate_axis('Z', spline_points[0].tilt)
	hair_emitter.location = (0, 0, 0)
	#size emitter depending on radius
	radius_inverse = 1 / spline_points[0].radius
	hair_emitter.scale = (radius_inverse, radius_inverse, radius_inverse)
	bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
	#add hair
	bpy.ops.object.particle_system_add()
	hair_settings = hair_emitter.particle_systems[0].settings
	hair_settings.type = 'HAIR'
	#limit field influence to the group that our curve is in
	#this ensures only THAT curve can influence this hair system
	hair_settings.effector_weights.collection = field_collection
	#todo: change based on curve length
	hair_settings.display_step = 5
	#hide emitter
	hair_emitter.show_instancer_for_render = False
	hair_emitter.show_instancer_for_viewport = False
	

class CurveToHair(bpy.types.Operator):
	"""Tooltip"""
	bl_idname = "object.curvetohair"
	bl_label = "Curve to Hair"

	@classmethod
	def poll(cls, context):
		return 1

	def execute(self, context):
		main(context)
		return {'FINISHED'}


def register():
	bpy.utils.register_class(CurveToHair)


def unregister():
	bpy.utils.unregister_class(CurveToHair)


if __name__ == "__main__":
	register()