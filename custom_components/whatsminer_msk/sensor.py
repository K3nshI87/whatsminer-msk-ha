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
    CONF_HOST,
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


SENSORS: tuple[WhatsminerSensorDescription, ...] = (
    WhatsminerSensorDescription(
        key="real_hash_rate",
        name="Real Hashrate",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:pickaxe",
        value_fn=lambda d: d.get("real_hash_rate"),
    ),
    WhatsminerSensorDescription(
        key="avg_hash_rate",
        name="Average Hashrate",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:pickaxe",
        value_fn=lambda d: d.get("avg_hash_rate"),
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
        value_fn=lambda d: float(d["water_temp"]) if d.get("water_temp") and d["water_temp"] != "0.00" else None,
    ),
    WhatsminerSensorDescription(
        key="running_time",
        name="Uptime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:clock-outline",
        value_fn=lambda d: d.get("running_time"),
    ),
    WhatsminerSensorDescription(
        key="psu_vin",
        name="PSU Voltage In",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("get.device.info", {}).get("msg", {}).get("power", {}).get("vin"),
    ),
    WhatsminerSensorDescription(
        key="psu_iin",
        name="PSU Current In",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("get.device.info", {}).get("msg", {}).get("power", {}).get("iin"),
    ),
    WhatsminerSensorDescription(
        key="psu_vout",
        name="PSU Voltage Out",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("get.device.info", {}).get("msg", {}).get("power", {}).get("vout"),
    ),
)


def _chain_sensors(chain_index: int) -> tuple[WhatsminerSensorDescription, ...]:
    i = chain_index
    return (
        WhatsminerSensorDescription(
            key=f"chain_{i}_hashrate",
            name=f"Chain {i} Hashrate",
            native_unit_of_measurement="TH/s",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:pickaxe",
            value_fn=lambda d, idx=i: _chain_val(d, idx, "hashrate"),
        ),
        WhatsminerSensorDescription(
            key=f"chain_{i}_freq",
            name=f"Chain {i} Frequency",
            native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:sine-wave",
            value_fn=lambda d, idx=i: _chain_val(d, idx, "freq"),
        ),
        WhatsminerSensorDescription(
            key=f"chain_{i}_temp_inlet",
            name=f"Chain {i} Temp Inlet",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda d, idx=i: _chain_val(d, idx, "temp_inlet"),
        ),
        WhatsminerSensorDescription(
            key=f"chain_{i}_temp_outlet",
            name=f"Chain {i} Temp Outlet",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda d, idx=i: _chain_val(d, idx, "temp_outlet"),
        ),
    )


def _chain_val(data: dict, chain_index: int, key: str) -> Any:
    chains = data.get("chain_info", [])
    for chain in chains:
        if chain.get("id") == chain_index:
            val = chain.get(key)
            if val is not None and isinstance(val, float):
                return round(val, 3)
            return val
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WhatsminerCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data

    chain_num = data.get("chain_num", 3)
    all_sensors = list(SENSORS)
    for i in range(chain_num):
        all_sensors.extend(_chain_sensors(i))

    async_add_entities(
        WhatsminerSensor(coordinator, entry, desc) for desc in all_sensors
    )


class WhatsminerSensor(CoordinatorEntity[WhatsminerCoordinator], SensorEntity):
    entity_description: WhatsminerSensorDescription

    def __init__(
        self,
        coordinator: WhatsminerCoordinator,
        entry: ConfigEntry,
        description: WhatsminerSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(coordinator, entry)

    @property
    def native_value(self) -> Any:
        if self.entity_description.value_fn is None:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except Exception:
            return None


def _device_info(coordinator: WhatsminerCoordinator, entry: ConfigEntry) -> DeviceInfo:
    data = coordinator.data or {}
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=data.get("miner_type", "WhatsMiner"),
        manufacturer=data.get("miner_factory", "WhatsMiner").capitalize(),
        model=data.get("miner_type", "Unknown"),
        sw_version=data.get("version"),
        configuration_url=f"http://{coordinator.host}",
    )
