# xiaomi_miio_ng for homeassistant

> [!NOTE]
> This is currently aimed for developers and reporting issues alone is not that helpful. If you want to contribute, consider writing PRs :-)

This repository hosts a custom component implementation of the homeassistant's xiaomi_miio integration rewrite (based on python-miio 0.6+).
The aim of this repository is to enable collaboration on the rewrite easier, and it is not aimed for end users.

If you want to help but do not have a device, you can use [the simulators shipped with python-miio](https://python-miio.readthedocs.io/en/latest/simulator.html) to some extent.

> [!WARNING]
> This uses the same DOMAIN (xiaomi_miio) as the built-in integration, so it WILL (likely) break your installation at some point. Use only for development and testing. You have been warned.

## Generic platforms

These platforms present generic entities that are available on all devices.
[All python-miio supported devices with descriptors](https://github.com/rytilahti/python-miio/issues/1617) will create relevant entities using these platforms.

* [x] `binary_sensor`
* [x] `button`
* [x] `diagnostics`
* [x] `number`
* [x] `select`
* [x] `sensor`
* [x] `switch`
* [ ] `update`

## Integration platforms

These platforms include some special handling and/or they just "bundle" the generic platforms together for better UX.
A checked checkbox means that at least some of the features have been already implemented.

* [ ] `air_quality`
* [ ] `alarm_control_panel`
* [ ] `camera`
* [ ] `device_tracker`
* [x] `fan`
* [ ] `humidifier`
* [x] `light`
* [ ] `media_player`
* [ ] `remote`
* [ ] `siren`
* [x] `vacuum`
* [ ] `water_heater`

## Tested devices

* `viomi.vacuum.v8`
* `yeelink.light.bslamp1`
* `yeelink.light.mono6` (genericmiot & yeelight)
* `zimi.powerstrip.v2`

## TODO
* [ ] Upgrade existing config entries. This one uses the device_id (instead of mac) as a unique identifier.
* [ ] Use "reconfigure" step for changing between regular & force_miot
* https://github.com/rytilahti/python-miio/issues/1114 for python-miio todos.
* Bases on https://github.com/rytilahti/home-assistant/commit/2498abe75fe3785a89016f9ada2a48925d0a45f0
