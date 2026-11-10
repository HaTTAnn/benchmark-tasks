"""Task-local safety observations after every physics scene update, outside resets."""
import types

def install(environment, callback):
 scene=environment.unwrapped.scene
 scene._battery_monitor_active=True
 if getattr(scene,'_battery_monitor',False): return
 previous=scene.update
 def update(self,dt,*a,**k):
  result=previous(dt,*a,**k)
  if self._battery_monitor_active:callback(environment,float(dt))
  return result
 scene.update=types.MethodType(update,scene)
 reset=environment.reset
 def reset_hook(*a,**k):
  # The embodiment settles objects after this call. Its real on_reset callback
  # re-enables tracking only after the entire reset/settling sequence finishes.
  scene._battery_monitor_active=False
  return reset(*a,**k)
 environment.reset=reset_hook
 scene._battery_monitor=True
