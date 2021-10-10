import bpy
import math
import mathutils
from math import radians

def main(context):
	#get selected object
	curve_object = bpy.context.active_object
	#check that it is a curve
	if(curve_object.type != 'CURVE'):
		return
	
	curve_data = curve_object.data
	
	#check bevel mode. profile is not YET supported
	if(curve_data.bevel_mode == 'PROFILE'):
		#todo: support profile mode
		return
	
	#make sure the curve actually has a bevel object
	if(curve_data.bevel_mode == 'OBJECT' and curve_data.bevel_object == None):
		return
	
	curve_object.display_type = 'WIRE'
	curve_object.hide_render = True
	#for cycles viewport
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
	
	first_spline_point = curve_data.splines[0].bezier_points[0];
	#calculate rotation of the hair emitter
	first_spline_handle_direction = first_spline_point.co - first_spline_point.handle_right
	hair_emitter_normal = mathutils.Vector(first_spline_handle_direction).normalized()
	hair_emitter_rotation = hair_emitter_normal.to_track_quat('Z', 'Y')
	#rotate hair_emitter_rotation by the tilt of the first spline point
	#hair_emitter_rotation.rotate(mathutils.Quaternion(hair_emitter_normal, -first_spline_point.tilt))
	#and radius
	hair_emitter_radius = curve_data.bevel_depth / first_spline_point.radius
	
	hair_emitter = None
		
	#todo: avoid using bpy.ops
	if(curve_data.bevel_mode == 'ROUND'):	
		#create circle with radius of round bevel curve
		bpy.ops.mesh.primitive_circle_add(fill_type='TRIFAN', radius = hair_emitter_radius, rotation = hair_emitter_rotation.to_euler(), location = (0, 0, 0))
		#the newly created circle is selected, so grab it from context
		hair_emitter = bpy.context.active_object
	elif(curve_data.bevel_mode == 'OBJECT'):
		bpy.ops.object.select_all(action='DESELECT')
		bpy.context.view_layer.objects.active = curve_data.bevel_object
		curve_data.bevel_object.select_set(True)
		bpy.ops.object.duplicate_move()
		hair_emitter = bpy.context.active_object
		bpy.ops.object.convert(target='MESH')
		bpy.ops.object.editmode_toggle()
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.edge_face_add()
		bpy.ops.object.editmode_toggle()
		hair_emitter.parent = curve_object
		hair_emitter.rotation_euler = hair_emitter_rotation.to_euler()
		hair_emitter.rotation_euler.rotate_axis('Z', -first_spline_point.tilt)
		hair_emitter.location = (0, 0, 0)
		#for some reason, spline point tilts twist hairs in the opposite direction from what is expected
		#this is the only way I can think to fix the issue: flipping all the spline point tilts :(
		for spline_point in curve_data.splines[0].bezier_points:
			spline_point.tilt = -spline_point.tilt
		
	hair_emitter.parent = curve_object
	bpy.ops.object.particle_system_add()
	hair_settings = hair_emitter.particle_systems[0].settings
	hair_settings.type = 'HAIR'
	#make sure only the curve we want to influence the hair actually influences the hair
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