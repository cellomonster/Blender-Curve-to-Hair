bl_info = {
    "name": "Curve to Hair",
    "description": "Create a hair emitter that follows a selected curve",
    "author": "Julian 'cellomonster' Triveri",
    "version": (0, 2),
    "blender": (2, 80, 0),
    "location": "Object > Convert > Curve to Hair",
    "warning": "WIP", # used for warning icon and text in addons panel
    "tracker_url": "https://github.com/cellomonster/Blender-Curve-to-Hair/issues",
    "support": "COMMUNITY",
    "category": "Convert",
}

import bpy
import math
import mathutils
import bmesh
#import faulthandler
from math import radians

def main(context):
	#faulthandler.enable()
	for curve_object in bpy.context.selected_objects:
		#check that selected object is a curve
		if curve_object.type != 'CURVE':
			continue
		
		curve_data = curve_object.data
		
		#check bevel mode. profile is not supported (yet)
		#todo: support profile mode
		if curve_data.bevel_mode == 'PROFILE':
			continue
		
		#if ROUND, check that round bevel curve has depth
		if curve_data.bevel_mode == 'ROUND' and curve_data.bevel_depth == 0:
			continue
		
		#if OBJECT, make sure the curve actually has a bevel object
		if curve_data.bevel_mode == 'OBJECT' and curve_data.bevel_object == None:
			continue
		
		spline = curve_data.splines[0]
		spline_points = None
		
		is_bezier = False
		spline_p0 = None
		pos_2 = None
		#calculate rotation of the hair emitter
		#points are different depending on if the curve is a NURBS or bezier curve
		if spline.type == 'BEZIER':
			spline_points = spline.bezier_points
			pos_2 = spline_points[0].handle_right
			is_bezier = True
		elif spline.type == 'NURBS':
			spline_points = spline.points
			pos_2 = spline_points[1].co.xyz
		else:
			continue
		
		spline_p0 = spline_points[0]
		
		#calculate rotation of the hair emitter
		hair_em_norm = mathutils.Vector(spline_p0.co.xyz - pos_2)
		hair_emitter_rotation = hair_em_norm.to_track_quat('Z', 'Y')
		
		#create a collection for the field to influence and add the curve to it
		field_collection = bpy.context.blend_data.collections.new(name='curve to hair col')
		field_collection.use_fake_user = True
		field_collection.objects.link(curve_object)
		
		#required
		curve_data.use_path = True
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
		
		#rescale curve so that first spline point radius is 1
		#this is needed for child hairs to work as expected
		scale = spline_p0.radius
		curve_origin = curve_object.location
		for spline_point in spline_points:
			spline_point.co /= scale
			#bezier point handles must also be moved
			if is_bezier:
				spline_point.handle_right /= scale
				spline_point.handle_left /= scale
			spline_point.radius /= scale
			#tilt is flipped as hairs twist opposite of tilt
			spline_point.tilt = -spline_point.tilt
		curve_object.scale *= scale
		
		#create hair emitter
		hair_emitter = None
		#if ROUND, the emitter is a disk matching the circle resolution of the bevel
		if curve_data.bevel_mode == 'ROUND' :
			mesh = bpy.data.meshes.new('hair emitter mesh')
			hair_emitter = bpy.data.objects.new('hair emitter', mesh)
			#create circle with radius of round bevel curve
			bm = bmesh.new()
			bm.from_mesh(hair_emitter.data)
			bmesh.ops.create_circle(bm, 
			                        cap_ends = True, 
			                        cap_tris = True, 
			                        segments = curve_data.bevel_resolution + 4, 
			                        radius = curve_data.bevel_depth)
			bm.to_mesh(hair_emitter.data)
			bm.free()
			
		#if BEVEL, create a new object with a mesh converted from the bevel object curve
		elif curve_data.bevel_mode == 'OBJECT' :
			#create a mesh version of the bevel object
			depsgraph = bpy.context.evaluated_depsgraph_get()
			object_eval = curve_data.bevel_object.evaluated_get(depsgraph)
			tmp_mesh = bpy.data.meshes.new_from_object(object_eval)    
			hair_emitter = bpy.data.objects.new(name='hair emitter', object_data = tmp_mesh)
			bm = bmesh.new()
			bm.from_mesh(hair_emitter.data)
			#create face from verts
			bmesh.ops.holes_fill(bm, edges = bm.edges, sides = len(bm.edges))
			bm.to_mesh(hair_emitter.data)
			bm.free()
			#todo apply scale after scaling hair_emitter
			hair_emitter.scale = curve_data.bevel_object.scale
			
		#link to view layer collection so the hairs are visible 
		bpy.context.view_layer.layer_collection.collection.objects.link(hair_emitter)
		
		#orient emitter
		hair_emitter.parent = curve_object
		hair_emitter.rotation_euler = hair_emitter_rotation.to_euler()
		hair_emitter.rotation_euler.rotate_axis('Z', spline_p0.tilt)
		hair_emitter.location = (0, 0, 0)
		#add hair
		hair_emitter.modifiers.new("part", type='PARTICLE_SYSTEM')
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
		
		if len(curve_object.material_slots) > 0:
			curve_mat = curve_object.material_slots[0].material
			hair_emitter.data.materials.append(curve_mat)

class CurveToHair(bpy.types.Operator):
	"""Tooltip"""
	bl_idname = "object.curvetohair"
	bl_label = "Curve to Hair"
	bl_options = {'UNDO'}

	@classmethod
	def poll(cls, context):
		return context.active_object.type == 'CURVE'

	def execute(self, context):
		main(context)
		return {'FINISHED'}
	
def menu_func(self, context):
	layout = self.layout
	layout.operator(CurveToHair.bl_idname)
	
def context_menu_func(self, context):
	if context.active_object.type != 'CURVE':
		return
	layout = self.layout
	layout.separator()
	layout.operator(CurveToHair.bl_idname)
		


def register():
	bpy.utils.register_class(CurveToHair)
	
	#prevent duplicate menu entries
	if hasattr(bpy.types, bpy.ops.object.curvetohair.idname()):
		return
	bpy.types.VIEW3D_MT_object_convert.append(menu_func)
	bpy.types.VIEW3D_MT_object_context_menu.append(context_menu_func)


def unregister():
	bpy.utils.unregister_class(CurveToHair)
	bpy.types.VIEW3D_MT_object_convert.remove(menu_func)
	bpy.types.VIEW3D_MT_object_context_menu.remove(context_menu_func)


if __name__ == "__main__":
	register()