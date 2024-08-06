"""
MIT License

Copyright (c) 2024 Daoming Chen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import coacd
import trimesh
import copy
import argparse
from urdf_parser_py.urdf import URDF, Mesh
from lxml import etree

def remove_collisions_from_xml(xml_string):
    root = etree.fromstring(xml_string)
    for link in root.xpath("//link"):
        for collision in link.xpath("collision"):
            link.remove(collision)
    return etree.tostring(root, encoding="unicode")

def add_new_collisions(xml_string, new_collisions):
    root = etree.fromstring(xml_string)
    for link_name, collisions in new_collisions.items():
        link = root.xpath(f"//link[@name='{link_name}']")[0]
        for collision in collisions:
            link.append(collision.to_xml())
    return etree.tostring(root, encoding="unicode", pretty_print=True)

# Parse arguments
parser = argparse.ArgumentParser(description='URDF Collision Modifier')
parser.add_argument('-u', '--urdf', type=str, required=True, help='URDF file path')
parser.add_argument('-m', '--mesh_dir', type=str, required=True, help='Mesh directory path')
parser.add_argument('-t', '--threshold', type=float, default=0.2, help='concavity threshold for terminating the decomposition (0.01~1), default = 0.05')
parser.add_argument('-pr', '--preprocess_resolution', type=int, default=50, help='resolution for manifold preprocess (20~100), default = 50.')
args = parser.parse_args()

# Load URDF
urdf_base, urdf_ext = os.path.splitext(args.urdf)
urdf_path_parts = urdf_base.split('/')
robot_name = urdf_path_parts[-1]
urdf_path = '/'.join(urdf_path_parts[:-1])

if urdf_ext.lower() == '.urdf':
    with open(args.urdf, 'r', encoding='utf-8') as file:
        robot_urdf = file.read().encode('utf-8')
    robot = URDF.from_xml_string(robot_urdf)
else:
    print('Invalid input file format. Please provide a .urdf file.')
    exit()

# Process collisions
total_num_collisions = 0
new_collisions = {}
for link in robot.links:
    print(f'Processing link: {link.name}')
    new_collisions[link.name] = []
    for collision in link.collisions:
        if isinstance(collision.geometry, Mesh):
            collision_mesh_file = collision.geometry.filename
            mesh_base, mesh_ext = os.path.splitext(collision_mesh_file)
            mesh_path_parts = collision_mesh_file.split('/')
            mesh_name = mesh_path_parts[-1]
            
            collision_mesh_file = os.path.join(args.mesh_dir, mesh_name)
            print(f'Processing collision geometry: {mesh_name}')
            
            # Decompose mesh using coacd
            mesh = trimesh.load(collision_mesh_file)
            mesh = coacd.Mesh(mesh.vertices, mesh.faces)
            parts = coacd.run_coacd(mesh, threshold=args.threshold, 
                                    preprocess_resolution=args.preprocess_resolution)
            
            # Save decomposed meshes and create new collisions
            total_num_collisions += len(parts)
            for k, part in enumerate(parts):
                v, f = part
                mesh2 = trimesh.Trimesh(v, f)
                export_name = f'{mesh_name}_{k}.stl'
                export_path = os.path.join(args.mesh_dir, export_name)
                mesh2.export(export_path)
                
                new_collision = copy.deepcopy(collision)
                new_collision.geometry.filename = f'file://{export_path}'
                new_collisions[link.name].append(new_collision)
        else:
            print(f'Not a mesh, keeping original collision')
            new_collisions[link.name].append(collision)
            total_num_collisions += 1

print(f'There are {len(total_num_collisions)} collisions meshes in the robot')

# Modify URDF XML
urdf_xml = robot.to_xml_string()
urdf_xml = remove_collisions_from_xml(urdf_xml)
urdf_xml = add_new_collisions(urdf_xml, new_collisions)

# Save modified URDF
new_urdf_path = os.path.join(urdf_path, f'{robot_name}_decomposed.urdf')
with open(new_urdf_path, 'w') as f:
    f.write(urdf_xml)
print(f'New URDF saved to {new_urdf_path}')