# BLUETTI Modbus Data Map

Цей файл зібраний на основі історичного reverse-engineering Android-додатка PowerOak/BLUETTI:
`modbusDataHandleV2` у `ConnectManager.java` і parser-ів із `ProtocolParserV2.java`.

Оригінальні Android source-файли не є частиною цього standalone репозиторію. Цей документ
залишено як практичну карту register groups для подальшої розробки `bluetti-venus-gateway`.

Мета:

- мати одну карту `addr -> parser -> ключові поля`
- швидко розуміти, що саме можна poll-ити
- мати окремий practical shortlist для `EP760 / PBOX`

## Як читати карту

- `addr`: Modbus register address, який передається в `getReadTask(...)`
- `parser`: який parser викликається в `modbusDataHandleV2`
- `result type`: який тип об'єкта виходить із parser-а
- `ключові поля`: короткий high-signal список, не завжди повний
- якщо parser не використовується і в bus летить сирий список/рядок, це позначено окремо

## Повна Карта `modbusDataHandleV2`

| addr | parser / handler | result type | ключові поля / зміст |
|---|---|---|---|
| `1` | `ProtocolParse.parseBaseConfig(...)` | `DeviceBaseConfigBean` | `protocolVer`, `iotModbusVer`, `specs`, `voltageType`, базова конфігурація девайса |
| `100` | `ProtocolParserV2.parseHomeData(...)` | `DeviceHomeData` | `packTotalSoc`, `packTotalVoltage`, `packTotalCurrent`, `totalACPower`, `totalGridPower`, `totalPVPower`, `deviceModel`, `deviceSN`, `energyLines`, `ctrlStatus`, `rateVoltage`, `rateFrequency` |
| `720` | `ProtocolParserV2.parseOTAStatus(...)` | `OTAStatus` | статус OTA, прогрес, етап оновлення |
| `1100` | `ProtocolParserV2.parseInvBaseInfo(...)` | `InvBaseInfo` | базова інформація інвертора, `devVoltageType`, версії, статуси, ідентифікація інвертора |
| `1200` | `ProtocolParserV2.parseInvPVInfo(...)` | `InvPVInfo` | `totalPVPower`, список PV phase/string, `inputVoltage`, `inputCurrent`, типи PV-входів |
| `1300` | `ProtocolParserV2.parseInvGridInfo(...)` | `InvGridInfo` | `frequency`, `totalChgPower`, `totalChgEnergy`, `totalFeedbackEnergy`, per-phase `gridVoltage`, `gridCurrent`, `gridPower`, `apparent` |
| `1400` | `ProtocolParserV2.parseInvLoadInfo(...)` | `InvLoadInfo` | DC/AC load power, energy, per-phase `loadVoltage`, `loadCurrent`, `loadPower` |
| `1500` | `ProtocolParserV2.parseInvInvInfo(...)` | `InvInvInfo` | інверторний вихід, AC side telemetry, output voltage/current/power/freq |
| `1700` | `ProtocolParserV2.parseInvMeterInfo(...)` | `InvMeterInfo` | meter model/SN, meter telemetry, phase power/voltage/current |
| `1900` | `ProtocolParserV2.parseInvMeterSettings(...)` | `InvMeterSettings` | налаштування meter-а |
| `2000` | `ProtocolParserV2.parseInvBaseSettings(...)` | `InvBaseSettings` | базові налаштування інвертора |
| `2200` | `ProtocolParserV2.parseInvAdvSettings(...)` | `InvAdvancedSettings` | advanced settings, EMS/control-related поля |
| `2280` | `ProtocolParserV2.heatPumpEnableParse(...)` | `HeatPumpEnable` | heat pump enable/status |
| `2400` | `ProtocolParserV2.parseCertSettings(...)` | `DeviceCertSettings` | certificate/certification settings |
| `2500` | `ProtocolParserV2.parseMicroInvAdvSettings(...)` | `MicroInvAdvSettings` | розширені налаштування micro inverter |
| `3000` | `ProtocolParse.parseFaultHistory(...)` | `DeviceFaultHistoryPage` | історія fault-ів, fault list, MQTT topic binding |
| `3500` | `ProtocolParserV2.parseTotalEnergyInfo(...)` | `InvEnergyStatistics` | total energy counters, aggregate energy statistics |
| `3600` | `ProtocolParserV2.parseCurrYearEnergy(...)` | `InvCurrentYearEnergy` | енергія за поточний рік |
| `4200` | `ProtocolParserV2.wtInfoParse(...)` | `WTInfo` | дані WT-модуля |
| `4400` | `ProtocolParserV2.wtSettingsParse(...)` | `WTSettings` | налаштування WT |
| `5000` | `ProtocolParserV2.parseTimeCtrlInfo(...)` | `DeviceTimeCtrlInfo` | time-control / schedule info |
| `6000` | `ProtocolParserV2.parsePackMainInfo(...)` | `PackMainInfo` | агрегована battery pack інформація: voltage/current/SOC/status/error bits |
| `6100` | `ProtocolParserV2.parsePackItemInfo(...)` | `PackItemInfo` | детальна інформація одного pack-а: pack ID, voltage/current/SOC/temp/status |
| `6300` | `ProtocolParserV2.parsePackSubPackInfo(...)` | `PackSubPackInfo` | sub-pack / module level дані |
| `7000` | `ProtocolParserV2.parsePackSettingsInfo(...)` | `PackSettingsInfo` | налаштування pack-а |
| `7200` | raw `listSubList` | raw list | сирі BMU bytes, окремий parser у `modbusDataHandleV2` не застосовується |
| `11000` | `ProtocolParserV2.parseIOTInfo(...)` | `DeviceIotInfo` | IoT module info: version, MAC/BLE MAC, network mode, signal, IDs |
| `11106` | `ProtocolParserV2.parseWifiInfo(...)` | `DeviceWiFiInfo` | Wi-Fi config/info |
| `11127` | `ProtocolParse.getASCIIStr(...)` | `String` | IoT server BLE SN |
| `12002` | `ProtocolParserV2.parseIOTSettingsInfo(...)` | `IOTSettingsInfo` | IoT settings/config |
| `12161` | `ProtocolParserV2.parseIOTEnableInfo(...)` | `IoTCtrlStatus` | enable flags для IoT |
| `12163` | `ProtocolParserV2.parseDisasterWarningInfo(...)` | `DisasterWarningData` | disaster warning mode/settings |
| `12174` | raw `listSubList` | raw list | subnet/gateway/network bytes |
| `12205` | `ProtocolParserV2.parseIoTDisplaySettings(...)` | `IoTDisplaySettings` | display/UI-related IoT settings |
| `13088` | `ProtocolParserV2.parseIoTMatterInfo(...)` | `IoTMatterInfo` | Matter pairing / fabric info |
| `13500` | `ProtocolParserV2.parseIOTWiFiMesh(...)` | `IoTWifiMesh` | Wi-Fi mesh info |
| `13603` | `joinToString(listSubList)` | `String` | IoT server key / hex string |
| `13611` | `ProtocolParserV2.parseMultWifi1(...)` | `DeviceWiFiInfo` | Wi-Fi station block 1 |
| `13624` | `ProtocolParserV2.parseMultWifi2(...)` | `DeviceWiFiInfo` | Wi-Fi station block 2 |
| `13776` | `ProtocolParse.getASCIIStr(...)` | `String` | BLE client pair SN |
| `14000` | `ProtocolParserV2.parseHmiInfo(...)` | `DeviceHmiInfo` | HMI/device screen info |
| `14500` | `SmartPlugParser.baseInfoParse(...)` | `SmartPlugInfoBean` | smart plug base telemetry/model/SN |
| `14700` | `SmartPlugParser.settingsInfoParse(...)` | smart plug settings bean | smart plug settings |
| `15000` | `ChargingPileProtParse.baseInfoParse(...)` | charging pile info bean | charging pile telemetry |
| `15500` | `DCDCParser.baseInfoParse(...)` | `DCDCInfo` | DCDC base telemetry/model/SN |
| `15600` | `DCDCParser.settingsInfoParse(...)` | `DCDCSettings` | DCDC settings |
| `15700` | `ProtocolParserV2.dcHubInfoParse(...)` | `DeviceDcHubInfo` | DC hub info/model/SN |
| `15750` | `ProtocolParserV2.dcHubSettingsParse(...)` | `DCHUBSettings` | DC hub settings |
| `16000` | `PanelParser.panelInfoParse(...)` | panel info bean | panel base info |
| `16100` | `PanelParser.dcAcInfoParse(..., false)` | panel DC info bean | panel DC telemetry |
| `16200` | `PanelParser.dcAcInfoParse(..., true)` | panel AC info bean | panel AC telemetry |
| `16400` | `PanelParser.baseSettingsParse(...)` | panel settings bean | panel settings |
| `17000` | `ProtocolParserV2.atsInfoParse(...)` | `DeviceAtsInfo` | ATS info |
| `17100` | `AT1Parser.at1InfoParse(...)` | AT1 info bean | AT1 base telemetry |
| `17400` | `AT1Parser.at1SettingsParse(...)` | AT1 settings bean | AT1 settings part 1 |
| `18000` | `EpadParser.baseInfoParse(...)` | EPAD base info bean | EPAD base info |
| `18300` | `EpadParser.baseSettingsParse(...)` | EPAD settings bean | EPAD base settings |
| `18400` | `EpadParser.baseLiquidPointParse(...)` | EPAD liquid point bean | liquid point block 1 |
| `18500` | `EpadParser.baseLiquidPointParse(...)` | EPAD liquid point bean | liquid point block 2 |
| `18600` | `EpadParser.baseLiquidPointParse(...)` | EPAD liquid point bean | liquid point block 3 |
| `19000` | `ProtocolParserV2.commSOCSettingsParse(...)` | SOC threshold/settings bean | SOC thresholds |
| `19100` | `ProtocolParserV2.commDelaySettingsParse(...)` | device delay settings bean | delay settings |
| `19200` | `ProtocolParserV2.parseScheduledBackup(...)` | `DeviceScheduledBackup` | scheduled backup / charge-discharge schedule |
| `19300` | `ProtocolParserV2.commTimerSettingsParse(...)` | `DeviceCommTimerSettings` | timer settings summary |
| `19305` | `ProtocolParserV2.commTimerTaskListParse(..., 1)` | `AT1TimerSettings` / timer task list | timer tasks block 1 |
| `19365` | `AT1Parser.timerSettingsSL1SL2Parse(...)` | AT1 timer settings bean | SL1/SL2 timers |
| `19425` | `ProtocolParserV2.commTimerTaskListParse(..., 7)` | `AT1TimerSettings` / timer task list | timer tasks block 2 |
| `19485` | `AT1Parser.timerSettingsSL3SL4Parse(...)` | AT1 timer settings bean | SL3/SL4 timers |
| `21000` | `DeviceMsgHandler.nodeInfoMsgHandle(...)` | node-related events | node inventory/topology |
| `26001` | `TouTimeCtrlParser.parseTouTimeExt(...)` | TOU time control bean | tariff / TOU schedule |
| `29770` | `ProtocolParserV2.bootUpgradeSupportParse(...)` | `BootUpgradeSupport` | bootloader upgrade support |
| `29772` | `ProtocolParserV2.bootSoftwareInfoParse(...)` | `BootSoftwareItem` list | bootloader/software metadata |
| `30001` | `ProtocolParserV2.parseActiveInfo(...)` | `DataActiveInfo` | activation/active status, raw modbus msg also attached |
| `30901` | `ProtocolParserV2.testSettingsParse(...)` | `DeviceTestSettings` | test/debug settings |
| `40000` | `ProtocolParserV2.parseHomeStorageSettings(...)` or `hostFileLogParse(...)` | `HomeStorageSettingsBean` or file-log bean | home storage settings or RV host file log |
| `40127` | `ProtocolParserV2.parseHomeStorageSettings(...)` or `hostFileLogParse(...)` | `HomeStorageSettingsBean` or file-log bean | alternate block for same logic |
| `40044` | `ProtocolParserV2.parseCertSettingsExt(...)` | cert settings ext bean | certificate extension settings |
| `40181` | `ProtocolParserV2.parseAntiBackflowCert(...)` | `DeviceAntiBackflowCert` | anti-backflow certification/config |
| `40187` | `ProtocolParserV2.parseCertSettingsPart2(...)` | `CertSettingsPart2` | second cert settings block |
| `6300 <= addr < 7000` | `new PackCellReadTask(...)` | `PackCellReadTask` | split cell-level battery read, сирий список комірок/NTC/пакетів |

## EP760 / PBOX Practical Shortlist

Нижче не повна карта, а саме те, що має сенс для `EP760 / PBOX` у live polling і подальшому декодуванні.

### Уже підтверджено live

| addr | parser | навіщо poll-ити | ключові поля |
|---|---|---|---|
| `100` | `parseHomeData(...)` | головний загальний snapshot | `packTotalSoc`, `packTotalVoltage`, `packTotalCurrent`, `totalACPower`, `totalGridPower`, `totalPVPower`, `totalInvPower`, `energyLines`, `ctrlStatus`, `rateVoltage`, `rateFrequency` |
| `1300` | `parseInvGridInfo(...)` | реальна grid telemetry | `gridVoltage`, `gridCurrent`, `gridPower`, `frequency`, `totalChgPower`, `totalChgEnergy`, `totalFeedbackEnergy` |

### Дуже ймовірно корисні для EP760

| addr | parser | навіщо | ключові поля |
|---|---|---|---|
| `1100` | `parseInvBaseInfo(...)` | inventory / mode / тип мережі | inverter base info, `devVoltageType`, моделі/версії/статуси |
| `1200` | `parseInvPVInfo(...)` | PV telemetry | per-string `inputVoltage`, `inputCurrent`, PV power/type |
| `1400` | `parseInvLoadInfo(...)` | load side telemetry | AC/DC load power, per-phase load voltage/current |
| `1500` | `parseInvInvInfo(...)` | inverter output telemetry | output AC values, inverter operating data |
| `1700` | `parseInvMeterInfo(...)` | meter-specific telemetry | phase power/voltage/current, meter ID |
| `3500` | `parseTotalEnergyInfo(...)` | накопичувальні energy counters | total energy statistics |
| `3600` | `parseCurrYearEnergy(...)` | annual energy | counters за поточний рік |
| `6000` | `parsePackMainInfo(...)` | battery aggregate detail | pack summary, status bits, alarms/faults |
| `6100` | `parsePackItemInfo(...)` | battery pack detail | pack-level voltage/current/SOC/temp |
| `6300..6999` | `PackCellReadTask` / `parsePackSubPackInfo(...)` | cell-level deep debug | cell voltages, NTC, sub-pack split blocks |

### Для конфігурації, а не live power-flow

| addr | parser | навіщо |
|---|---|---|
| `1` | `parseBaseConfig(...)` | базова конфігурація, `protocolVer`, `iotModbusVer`, specs |
| `2000` | `parseInvBaseSettings(...)` | базові inverter settings |
| `2200` | `parseInvAdvSettings(...)` | advanced inverter settings |
| `7000` | `parsePackSettingsInfo(...)` | battery settings |
| `19000` | `commSOCSettingsParse(...)` | SOC threshold settings |
| `19100` | `commDelaySettingsParse(...)` | delay settings |
| `19200` | `parseScheduledBackup(...)` | scheduled backup |
| `19300` / `19305` / `19425` | timer parsers | time windows / timer tasks |
| `26001` | `parseTouTimeExt(...)` | TOU / tariff windows |

## Рекомендований Roadmap Для EP760

### Рівень 1. Мінімально достатній live logger

- `100` + `1300`
- уже дає:
  - `soc`
  - `battery_voltage_v`
  - `battery_current_a`
  - `ac_power_w`
  - `grid_power_w`
  - `grid_voltage_v`
  - `grid_current_a`
  - `grid_freq_hz`
  - `pv_power_w`
  - `energy flow`

### Рівень 2. Розширений power-flow

- додати `1200`, `1400`, `1500`
- це дасть:
  - PV string detail
  - load side detail
  - inverter output detail

### Рівень 3. Battery deep dive

- додати `6000`, `6100`, `6300..6999`
- це дасть:
  - pack health
  - temperature
  - cell-level detail
  - окремі alarm/fault/status блоки

### Рівень 4. Historical / settings / analytics

- `3500`, `3600`, `19000+`, `26001`
- це дасть:
  - aggregate counters
  - yearly energy
  - TOU/timers/settings

## Що Важливо Не Плутати

- `100 / HOME_INFO` дає aggregate snapshot, але не дає live `gridVoltage`.
- `1300 / INV_GRID_INFO` дає реальні `gridVoltage`, `gridCurrent`, `gridFreq`.
- Частина адрес повертає вже структурований bean, а частина лише raw list/string.
- Не всі адреси однаково корисні для `EP760`: `modbusDataHandleV2` охоплює багато серій девайсів, не тільки home power.

## Найкращі Наступні Кроки Для Цього Репозиторію

1. Тримати `100`, `1300`, `1400`, `1500` у синхроні з EP760 polling profile gateway.
2. Перевірити decoder-и для `6000` і `6100` на реальному payload перед увімкненням pack diagnostics.
3. Окремо розмапити `alarmBlockWords` і `faultBlockWords` у людинозрозумілі назви.
4. Додавати нові register groups тільки разом із тестами parser-а і Victron projection policy.
