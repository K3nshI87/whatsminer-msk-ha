from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WhatsminerCoordinator


@dataclass(frozen=True)
class WhatsminerSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], Any] | None = None
    unit_fn: Callable[[dict], str | None] | None = None


def _psu(data: dict) -> dict:
    return data.get("get.device.info", {}).get("msg", {}).get("power", {})


def _psu_fan(data: dict) -> float | None:
    psu_fan = _psu(data).get("fanspeed")
    if psu_fan is not None and psu_fan > 0:
        return psu_fan
    fans = [f for f in data.get("fan_speed", []) if f > 0]
    return round(sum(fans) / len(fans)) if fans else None


SENSORS: tuple[WhatsminerSensorDescription, ...] = (
    WhatsminerSensorDescription(
        key="real_hash_rate",
        name="Hashrate",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:pickaxe",
        value_fn=lambda d: d.get("real_hash_rate"),
        unit_fn=lambda d: d.get("rate_unit", "TH/s"),
    ),
    WhatsminerSensorDescription(
        key="avg_hash_rate",
        name="Avg Hashrate",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:pickaxe",
        value_fn=lambda d: d.get("avg_hash_rate"),
        unit_fn=lambda d: d.get("rate_unit", "TH/s"),
    ),
    WhatsminerSensorDescription(
        key="power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("power"),
    ),
    WhatsminerSensorDescription(
        key="temp_inlet",
        name="Temperature Inlet",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("temp", {}).get("inlet"),
    ),
    WhatsminerSensorDescription(
        key="temp_outlet",
        name="Temperature Outlet",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("temp", {}).get("outlet"),
    ),
    WhatsminerSensorDescription(
        key="water_temp",
        name="Water Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (
            float(d["water_temp"])
            if d.get("water_temp") and float(d.get("water_temp", 0)) > 0
            else None
        ),
    ),
    WhatsminerSensorDescription(
        key="psu_temp",
        name="PSU Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _psu(d).get("temp0"),
    ),
    WhatsminerSensorDescription(
        key="psu_fan",
        name="PSU Fan Speed",
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=_psu_fan,
    ),
    WhatsminerSensorDescription(
        key="psu_vin",
        name="PSU Voltage In",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _psu(d).get("vin"),
    ),
    WhatsminerSensorDescription(
        key="psu_iin",
        name="PSU Current In",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _psu(d).get("iin"),
    ),
    WhatsminerSensorDescription(
        key="uptime",
        name="Uptime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:clock-outline",
        value_fn=lambda d: round(d["running_time"] / 3600, 2) if d.get("running_time") else None,
    ),
    WhatsminerSensorDescription(
        key="miner_status",
        name="Status",
        icon="mdi:information-outline",
        value_fn=lambda d: d.get("miner_status"),
    ),
    WhatsminerSensorDescription(
        key="active_pool",
        name="Active Pool",
        icon="mdi:pool",
        value_fn=lambda d: next(
            (p["url"] for p in d.get("pools", []) if p.get("url")), None
        ),
    ),
)


def _chain_sensors(chain_index: int) -> tuple[WhatsminerSensorDescription, ...]:
    i = chain_index

    def _cv(key: str) -> Callable[[dict], Any]:
        def fn(d: dict, idx: int = i) -> Any:
            for chain in d.get("chain_info", []):
                if chain.get("id") == idx:
                    val = chain.get(key)
                    return round(val, 3) if isinstance(val, float) else val
            return None
        return fn

    return (
        WhatsminerSensorDescription(
            key=f"chain_{i}_hashrate",
            name=f"Chain {i} Hashrate",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:pickaxe",
            value_fn=_cv("hashrate"),
            unit_fn=lambda d: d.get("rate_unit", "TH/s"),
        ),
        WhatsminerSensorDescription(
            key=f"chain_{i}_freq",
            name=f"Chain {i} Frequency",
            native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:sine-wave",
            value_fn=_cv("freq"),
        ),
        WhatsminerSensorDescription(
            key=f"chain_{i}_temp_inlet",
            name=f"Chain {i} Temp Inlet",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=_cv("temp_inlet"),
        ),
        WhatsminerSensorDescription(
            key=f"chain_{i}_temp_outlet",
            name=f"Chain {i} Temp Outlet",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=_cv("temp_outlet"),
        ),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinators: dict[str, WhatsminerCoordinator] = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for coordinator in coordinators.values():
        chain_num = (coordinator.data or {}).get("chain_num", 3)
        descs = list(SENSORS)
        for i in range(chain_num):
            descs.extend(_chain_sensors(i))
        for desc in descs:
            entities.append(WhatsminerSensor(coordinator, entry, desc))
    async_add_entities(entities)


class WhatsminerSensor(CoordinatorEntity[WhatsminerCoordinator], SensorEntity):
    entity_description: WhatsminerSensorDescription

    def __init__(self, coordinator: WhatsminerCoordinator, entry: ConfigEntry, description: WhatsminerSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{coordinator.api.host}_{description.key}"
        self._attr_device_info = _device_info(coordinator, entry)
        if description.unit_fn is None and description.native_unit_of_measurement:
            self._attr_native_unit_of_measurement = description.native_unit_of_measurement

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.unit_fn and self.coordinator.data:
            return self.entity_description.unit_fn(self.coordinator.data)
        return self.entity_description.native_unit_of_measurement

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data or self.entity_description.value_fn is None:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except Exception:
            return None


def _device_info(coordinator: WhatsminerCoordinator, entry: ConfigEntry) -> DeviceInfo:
    data = coordinator.data or {}
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{coordinator.api.host}")},
        name=f"{data.get('miner_type', 'WhatsMiner')} ({coordinator.api.host})",
        manufacturer=(data.get("miner_factory") or "WhatsMiner").capitalize(),
        model=data.get("miner_type"),
        sw_version=data.get("version"),
        configuration_url=f"http://{coordinator.api.host}",
    )
