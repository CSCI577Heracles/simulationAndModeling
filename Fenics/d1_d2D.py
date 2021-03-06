"""
Project III Temperature flow in ice
Started from:
FEniCS tutorial demo program: Diffusion equation with Dirichlet
conditions and a solution that will be exact at all nodes.
"""
from __future__ import division
import ConfigParser  # reads INI files
from dolfin import *
version = dolfin.__version__
print 'dolfin version is', version
if version > '1.0.0':
    Interval = IntervalMesh
import numpy as np
import sys
import os
# import matplotlib.pyplot as pl
spy = 31557600.0  # sec/year = 60*60*24*365.25

# Helpers for commandline (CLI) inputs
argc = len(sys.argv) - 1
def get_arg(ix, default_value, cast_type=float):
    return cast_type(sys.argv[ix]) if argc > ix-1 else default_value

print 'args: surface temp, dt [years], total time [years], temp to warm to'
print ','.join(sys.argv)

# Get constants from an INI file
config = ConfigParser.SafeConfigParser()
config.read('constants.ini')
pairs_in_first_section = config.items(config.sections()[0])
# Need to use v2.6 dict syntax instead of dict comprehension
consts_dict = dict([(key, eval(value)) for key, value in pairs_in_first_section])  # can add globals() to second param of eval if constants depend on `spy`
globals().update(consts_dict)  # put constants into global namespace


## Variables (defaults pulled from INI file)
time_at_which_to_warm *= spy  # after equilibrium, add warming
do_warming = bool(time_at_which_to_warm)  # later changed/used as a signal
temperature_0 = get_arg(1, temperature_0)  # constant added to sin function
dt = get_arg(2, dt) * spy
total_sim_time = get_arg(3, total_sim_time) * spy
temp_to_warm_to = get_arg(4, temp_to_warm_to)
# enforce_pmp = True
# theta0_multiplier = 5.0  # multiplied by the sin function
# u_mult = 20.0  # TODO np.linspace(20, 100, 10)  # h_coeff
# w_mult = 0.5  # TODO np.linspace(0.1, 0.5, 10)  # v_coeff
# d_theta_dx = 1.01e-4  # TODO np.linspace(1, 5, 10)*10**-4 # deg C/m, horizontal temperature gradient
# surface_slope = 0.1e-5  # TODO np.linspace(0.1, 1, 10)*10**-5  # dzs_dx
# qgeo = 42e-3  # TODO np.linspace(30, 70, 10)*10**-3, W/m^2, Geothermal heat flow
# mesh_node_count = 20

## Constants, pretty much
# z_b = 0.0  # bottom
# z_s = 1500.0  # surface
# k = 2.1  # W/(m*K), thermal diffusivity of ice
# rho = 600.0  # kg/m^3, density of firn  # NOTE: Use firn for only the first part (how deep does seasonal variation go)
# rho = 911.0  # kg/m^3, Density of ice
# cp = 2009.0  # J/(kg*K), Heat capacity
# g = 9.81  # m/s^2 accel due to gravity
# beta = 9.8e-8  # K/Pa, Pressure dependence of melting point

naming_parameters_str = "dt={dt} te0={te0} warm_ti={warm_ti} te_warm={te_warm}".format(
    dt=dt, warm_ti=time_at_which_to_warm, te0=temperature_0, te_warm=temp_to_warm_to)


## Fenics simulation stuff =========================================
def theta_pmp(z_arr):
    return beta * rho * g * (z_arr - z_s)  # deg C, Pressure melting point of ice

# Create mesh and define function space
mesh = Interval(mesh_node_count, z_b, z_s)
node_coords = mesh.coordinates()
print 'node_coords', node_coords
theta_pmp_arr = theta_pmp(node_coords)
theta_pmp_arr = theta_pmp_arr.reshape(theta_pmp_arr.size, )
# NOTE: Need to reshape array to match nodes shape
print 'theta_pmp_arr', theta_pmp_arr
func_space = FunctionSpace(mesh, 'Lagrange', 1)

# Define boundary conditions
theta_0 = Expression('t0 + m*sin(2.0*pi*(t/spy))',  # sin and pi are keywords
                     t0=temperature_0, m=theta0_multiplier, t=0, spy=spy)


def boundary(x, on_boundary):
    epsilon = 1e-14
    return on_boundary and abs(x[0] - z_s) < epsilon

dirichlet_bc = DirichletBC(func_space, theta_0, boundary)

# Initial condition
theta_1 = interpolate(theta_0, func_space)
#theta_1 = project(theta_0, func_space)  # will not result in exact solution!

# Define variational problem
theta = TrialFunction(func_space)
v = TestFunction(func_space)

sigma = '((x[0] - {z_b})/({z_s} - {z_b}))'.format(
        z_s=z_s, z_b=z_b)
print 'sigma:', sigma
u_prime = '-4*{m}*pow({s}, 3)/({zs}-{zb})'.format(
          s=sigma, m=u_mult, zs=z_s, zb=z_b)
print 'u_prime:', u_prime
u = Expression('m * pow({s}, 4)/spy'.format(s=sigma),
               m=u_mult, spy=spy)  # m/annum, horiz ice velocity
w_str = '-m*'+sigma+'/spy'
if version > '1.0.0':
    w_str = (w_str, )  # (needs to be a tuple to work with `inner`)
w = Expression(w_str, m=w_mult, spy=spy)  # m/annum, vertical ice velocity
phi = Expression('-p*g*(zs-x[0])*{du_dz}*dzs_dx'.format(du_dz=u_prime),
                 p=rho, g=g, zs=z_s, dzs_dx=surface_slope)  # W/m^3, heat sources from deformation of ice

bed_boundary = Expression('1 - {s}'.format(s=sigma))
neumann_bc = qgeo/rho/cp * dt * bed_boundary * v * ds
# neumann_bc = g * dt * v * ds  # Will's code

diffusion_term = theta*v + \
    (k/rho/cp) * inner(nabla_grad(theta), nabla_grad(v))*dt
# Either of the following seem to work in v1.0.0
# NOTE: Seems that we shouldn't negate w here
vertical_advection = inner(w, nabla_grad(theta)) * v * dt
# vertical_advection = w * nabla_grad(theta) * v * dt  # doesn't work in v1.1.0
horiz_advection = -u * d_theta_dx * v * dt
strain_heating = phi/rho/cp * Expression(u_prime)/spy * v * dt

a = (diffusion_term + vertical_advection)*dx
# L = (theta_1 - u*d_theta_dx*dt + phi/rho/cp * dt)*v*dx + neumann_bc
L = (theta_1*v + horiz_advection + strain_heating)*dx + neumann_bc

A = assemble(a)   # assemble only once, before the time stepping
b = None          # necessary for memory saving assemeble call
# Compute solution
theta = Function(func_space)   # the unknown at a new time level

## Time loop
t = dt
out_file = File("results/theta.pvd")
while t <= total_sim_time:
    print 'time = {t:.1f} years'.format(t=t / spy)
    b = assemble(L, tensor=b)
    theta_0.t = t
    dirichlet_bc.apply(A, b)
    solve(A, theta.vector(), b)

    # Keep temperatures within PMP
    if enforce_pmp:
        temp = theta.vector().array()
        mask_ixs_gt_pmp = temp > theta_pmp_arr
        if np.any(mask_ixs_gt_pmp):
            print 'ixs_gt_pmp', np.where(mask_ixs_gt_pmp)
        temp[mask_ixs_gt_pmp] = theta_pmp_arr[mask_ixs_gt_pmp]
        theta.vector()[:] = temp

    # TODO can we set the x,ylim?
    plot(theta, title=naming_parameters_str)  # transpose of the plot we want
    out_file << (theta, t)

    # Verify
    u_e = interpolate(theta_0, func_space)
    maxdiff = np.abs(u_e.vector().array() - theta.vector().array()).max()
    print 'Max error, t=%.2f: %-10.3f' % (t, maxdiff)

    t += dt
    theta_1.assign(theta)

    # Add global warming
    if do_warming and t >= time_at_which_to_warm:
        do_warming = False
        theta_0.t0 = temp_to_warm_to

interactive()
