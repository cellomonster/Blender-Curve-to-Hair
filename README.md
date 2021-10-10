# Blender-Curve-to-Hair
Blender operator to create particle hairs from beveled Bézier curves

⚠️ You must run the curvetohair.py before using the macro. The operator is named 'Curve to Hair.' You can find it by searching 'Curve to Hair' in the F3 search menu.

⚠️ The hair emitter will not follow the first curve point if you edit the curve. If you want to change where the curve 'starts,' you'll need to move the whole curve.

⚠️ Hairs don't perfectly follow curves with lots of twisting. 

⚠️ When using the operator on a curve, the curve's tilt will be flipped. This is done because hairs twist in the opposite direction of curve tilt.

⚠️ Does not support curves with the 'Profile' bevel type. 'Round' and 'Object' bevels are supported

![screenshot](screenshot.png)
