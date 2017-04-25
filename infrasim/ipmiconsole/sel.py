'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from .common import logger, msg_queue, send_ipmi_sim_command

# sensor number --> Event Type( 01, 02-0C, 6F ) --> sensor Type
#                    Event Type


# SEL Event

# threshold        01h      threshold based event
# Generic          02h-0Ch  discrete
# Sensor-specific  6Fh      discrete
# OEM              70h-7Fh  OEM

# SEL format
# event_code : { index : [generic_offset, event_data1, event_data2, event_data3, description] }
# map between Event/reading type code and event states
# will changed to XML/Jason format in feature
events_map = {
    0x01: {
        0x00: 'Lower Non-critical - going low',
        0x01: 'Lower Non-critical - going high',
        0x02: 'Lower Critical - going low',
        0x03: 'Lower Critical - going high',
        0x04: 'Lower Non-recoverable - going low',
        0x05: 'Lower Non-recoverable - going high',
        0x06: 'Upper Non-critical - going low',
        0x07: 'Upper Non-critical - going high',
        0x08: 'Upper Critical - going low',
        0x09: 'Upper Critical - going high',
        0x0A: 'Upper Non-recoverable - going low',
        0x0B: 'Upper Non-recoverable - going high'
    },

    0x02: {
        0x00: 'Transition to Idle',
        0x01: 'Transition to Active',
        0x02: 'Transition to Busy'
    },

    0x03: {
        0x00: 'State Deasserted',
        0x01: 'State Asserted'
    },

    0x04: {
        0x00: 'Predictive Failure deasserted',
        0x01: 'Predictive Failure asserted'
    },

    0x05: {
        0x00: 'Limit Not Exceeded',
        0x01: 'Limit Exceeded'
    },

    0x06: {
        0x00: 'Performance Met',
        0x01: 'Performance Lags'
    },

    0x07: {
        0x00: 'transition to OK',
        0x01: 'transition to Non-Critical from OK',
        0x02: 'transition to Critical from less severe',
        0x03: 'transition to Non-recoverable from less severe',
        0x04: 'transition to Non-Critical from more severe',
        0x05: 'transition to Critical from Non-recoverable ',
        0x06: 'transition to Non-recoverable',
        0x07: 'Monitor ',
        0x08: 'Informational'
    },

    0x08: {
        0x00: 'Device Removed / Device Absent ',
        0x01: 'Device Inserted / Device Present'
    },

    0x09: {
        0x00: 'Device Disabled',
        0x01: 'Device Enabled '
    },

    0x0A: {
        0x00: 'transition to Running',
        0x01: 'transition to In Test',
        0x02: 'transition to Power Off',
        0x03: 'transition to On Line',
        0x04: 'ransition to Off Line',
        0x05: 'transition to Off Duty',
        0x06: 'transition to Degraded',
        0x07: 'transition to Power Save',
        0x08: 'Install Error '
    },

    0x0B: {
        0x00: 'Fully Redundant (formerly .Redundancy Regained.) ',
        0x01: 'Redundancy Lost Entered any non-redundant state',
        0x02: 'Redundancy Degraded Redundancy still exists, but at a less than full level.',
        0x03: 'Non-redundant Entered from Redundancy Degraded or Fully Redundant',
        0x04: 'Non-redundant Entered from Non-redundant:Insufficient Resources',
        0x05: 'Non-redundant:Insufficient Resources Unit is non-redundant and has insufficient resources to maintain normal operation.',
        0x06: 'Redundancy Degraded from Fully Redundant Unit has lost some redundant resource(s) but is still in a redundant state',
        0x07: 'Entered from Non-redundant:Sufficient Resources or Non-redundant:Insufficient Resources'
    },

    0x0C: {
        0x00: 'D0 Power State',
        0x01: 'D1 Power State',
        0x02: 'D2 Power State',
        0x03: 'D3 Power State'
    },
}

# sensor type code : event states
sensor_specific_event_map = {
    # Physical Security (Chassis Intrusion)
    0x05: {
        0x00: [0x0, 0x0, 0x0, 'General Chassis Intrusion'],
        0x01: [0x1, 0x0, 0x0, 'Drive Bay intrusion'],
        0x02: [0x2, 0x0, 0x0, 'I/O Card area intrusion'],
        0x03: [0x3, 0x0, 0x0, 'Processor area intrusion'],
        0x04: [0x4, 0x0, 0x0, 'LAN Leash Lost (system is unplugged from LAN)'],
        0x05: [0x5, 0x0, 0x0, 'Unauthorized dock'],
        0x06: [0x6, 0x0, 0x0, 'FAN area intrusion (supports detection of hot plug fan tampering)'] },

    # Platform Security Violation Attempt
    0x06: {
        0x00: [0x0, 0x0, 0x0, 'Secure Mode (Front Panel Lockout) Violation attempt'],
        0x01: [0x1, 0x0, 0x0, 'Pre-boot Password Violation - user password'],
        0x02: [0x2, 0x0, 0x0, 'Pre-boot Password Violation attempt - setup password'],
        0x03: [0x3, 0x0, 0x0, 'Pre-boot Password Violation - network boot password'],
        0x04: [0x4, 0x0, 0x0, 'Other pre-boot Password Violation'],
        0x05: [0x5, 0x0, 0x0, 'Out-of-band Access Password Violation '] },

    # Processor
    0x07: {
        0x00: [0x0, 0x0, 0x0, 'IERR'],
        0x01: [0x1, 0x0, 0x0, 'Thermal Trip'],
        0x02: [0x2, 0x0, 0x0, 'FRB1/BIST failure '],
        0x03: [0x3, 0x0, 0x0, 'FRB2/Hang in POST failure '],
        0x04: [0x4, 0x0, 0x0, 'FRB3/Processor Startup/Initialization failure (CPU didn.t start) '],
        0x05: [0x5, 0x0, 0x0, 'Configuration Error'],
        0x06: [0x6, 0x0, 0x0, 'SM BIOS Uncorrectable CPU-complex Error'],
        0x07: [0x7, 0x0, 0x0, 'Processor Presence detected '],
        0x08: [0x8, 0x0, 0x0, 'Processor disabled'],
        0x09: [0x9, 0x0, 0x0, 'Terminator Presence Detected'],
        0x0A: [0xA, 0x0, 0x0, 'Processor Automatically Throttled'],
        0x0B: [0xB, 0x0, 0x0, 'Machine Check Exception (Uncorrectable)'],
        0x0C: [0xC, 0x0, 0x0, 'Correctable Machine Check Error']},

    # Power Supply (also used for  power converters [e.g. DC-to-DC converters]
    0x08: {
        0x00: [0x0,  0x0, 0x0, 'Presence detected '],
        0x01: [0x1,  0x0, 0x0, 'Power Supply Failure detected '],
        0x02: [0x2,  0x0, 0x0, 'Predictive Failure'],
        0x03: [0x3,  0x0, 0x0, 'Power Supply input lost (AC/DC)'],
        0x04: [0x4,  0x0, 0x0, 'Power Supply input lost or out-of-range'],
        0x05: [0x5,  0x0, 0x0, 'Power Supply input out-of-range, but presen'],
        0x06: [0x36,  0x0, 0x0, 'Configuration error.Vendor mismatch, for power supplies that include this status'],
        0x07: [0x36,  0x0, 0x1, 'Revision mismatch, for power supplies that include this status.'],
        0x08: [0x36,  0x0, 0x2, 'Processor missing'],
        0x09: [0x36,  0x0, 0x3, 'Power Supply rating mismatch'],
        0x0A: [0x36,  0x0, 0x4, 'Voltage rating mismatch'] },

    # Power Unit
    0x09: {
        0x00: [0x0, 0x0, 0x0, 'Power Off / Power Down '],
        0x01: [0x1, 0x0, 0x0, 'Power Cycle'],
        0x02: [0x2, 0x0, 0x0, '240VA Power Down'],
        0x03: [0x3, 0x0, 0x0, 'Interlock Power Down'],
        0x04: [0x4, 0x0, 0x0, 'AC lost / Power input lost '],
        0x05: [0x5, 0x0, 0x0, 'Soft Power Control Failure'],
        0x06: [0x6, 0x0, 0x0, 'Power Unit Failure detected'],
        0x07: [0x7, 0x0, 0x0, 'Predictive Failure'] },

    # Memory
    0x0C: {
        0x00: [0x0, 0x0, 0x0, 'Correctable ECC / other correctable memory error'],
        0x01: [0x1, 0x0, 0x0, 'Uncorrectable ECC / other uncorrectable memory error '],
        0x02: [0x2, 0x0, 0x0, 'Parity'],
        0x03: [0x3, 0x0, 0x0, 'Memory Scrub Failed (stuck bit)'],
        0x04: [0x4, 0x0, 0x0, 'Memory Device Disabled'],
        0x05: [0x5, 0x0, 0x0, 'Correctable ECC / other correctable memory error logging limit reached'],
        0x06: [0x6, 0x0, 0x0, 'Presence detected. Indicates presence of entity associated with the sensor'],
        0x07: [0x7, 0x0, 0x0, 'Configuration error. Indicates a memory configuration error for the entity associated with the sensor'],
        0x08: [0x8, 0x0, 0x0, 'Spare. Indicates entity associated with the sensor represents a spare unit of memory'],
        0x09: [0x9, 0x0, 0x0, 'Memory Automatically Throttled'],
        0x0A: [0xA, 0x0, 0x0, 'Critical Overtemperature'] },

    # Drive slot(bay)
    0x0D: {
        0x00: [0x0, 0x0, 0x0, 'Drive Presence'],
        0x01: [0x1, 0x0, 0x0, 'Drive Fault'],
        0x02: [0x2, 0x0, 0x0, 'Predictive Failure'],
        0x03: [0x3, 0x0, 0x0, 'Hot Spare'],
        0x04: [0x4, 0x0, 0x0, 'Consistency Check / Parity Check in progress'],
        0x05: [0x5, 0x0, 0x0, 'In Critical Array'],
        0x06: [0x6, 0x0, 0x0, 'In Failed Array '],
        0x07: [0x7, 0x0, 0x0, 'Rebuild/Remap in progress'],
        0x08: [0x8, 0x0, 0x0, 'Rebuild/Remap Aborted (was not completed normally)'] },

    # System Firmware Progress (formerly POST Error)
    0x0F: {
        0x00: [0x0, 0x0, 0x0, 'System Firmware Error (POST Error) '],
        0x01: [0x1, 0x0, 0x0, 'System Firmware Hang'],
        0x02: [0x2, 0x0, 0x0, 'System Firmware Progress'] },

    # Event logging disable
    0x10: {
        0x00: [0x0, 0x0, 0x0, 'Correctable Memory Error Logging Disabled '],
        0x01: [0x1, 0x0, 0x0, 'Event Type Logging Disabled'],
        0x02: [0x2, 0x0, 0x0, 'Log Area Reset/Cleared'],
        0x03: [0x3, 0x0, 0x0, 'All Event Logging Disabled'],
        0x04: [0x4, 0x0, 0x0, 'SEL Full'],
        0x05: [0x5, 0x0, 0x0, 'SEL Almost Full'],
        0x06: [0x6, 0x0, 0x0, 'Correctable Machine Check Error Logging Disabled'] },
    # watch dog 1
    0x11: {
        0x00: [0x0, 0x0, 0x0, 'BIOS Watchdog Reset '],
        0x01: [0x1, 0x0, 0x0, 'OS Watchdog Reset '],
        0x02: [0x2, 0x0, 0x0, 'OS Watchdog Shut Down'],
        0x03: [0x3, 0x0, 0x0, 'OS Watchdog Power Down'],
        0x04: [0x4, 0x0, 0x0, 'OS Watchdog Power Cycle'],
        0x05: [0x5, 0x0, 0x0, 'OS Watchdog NMI / Diagnostic Interrupt'],
        0x06: [0x6, 0x0, 0x0, 'OS Watchdog Expired, status only'],
        0x07: [0x7, 0x0, 0x0, 'OS Watchdog pre-timeout Interrupt, non-NMI'] },

    # System Event
    0x12: {
        0x00: [0x0, 0x0, 0x0, 'System Reconfigured '],
        0x01: [0x1, 0x0, 0x0, 'OEM System Boot Event '],
        0x02: [0x2, 0x0, 0x0, 'Undetermined system hardware failure'],
        0x03: [0x3, 0x0, 0x0, 'Entry added to Auxiliary Log'],
        0x04: [0x4, 0x0, 0x0, 'PEF Action'],
        0x05: [0x5, 0x0, 0x0, 'Timestamp Clock Synch.'] },

    # Critical Interrupt
    0x13: {
        0x00: [0x0, 0x0, 0x0, 'Front Panel NMI / Diagnostic Interrupt '],
        0x01: [0x1, 0x0, 0x0, 'Bus Timeout '],
        0x02: [0x2, 0x0, 0x0, 'I/O channel check NMI '],
        0x03: [0x3, 0x0, 0x0, 'Software NMI '],
        0x04: [0x4, 0x0, 0x0, 'PCI PERR'],
        0x05: [0x5, 0x0, 0x0, 'PCI SERR'],
        0x06: [0x6, 0x0, 0x0, 'EISA Fail Safe Timeout'],
        0x07: [0x7, 0x0, 0x0, 'Bus Correctable Error'],
        0x08: [0x8, 0x0, 0x0, 'Bus Uncorrectable Error '],
        0x09: [0x9, 0x0, 0x0, 'Fatal NMI (port 61h, bit 7)'],
        0x0A: [0xA, 0x0, 0x0, 'Bus Fatal Error'],
        0x0B: [0xB, 0x0, 0x0, 'Bus Degraded (bus operating in a degraded performance state)'] },

    # button and switch
    0x14: {
        0x00: [0x0, 0x0, 0x0, 'Power Button pressed'],
        0x01: [0x1, 0x0, 0x0, 'Sleep Button pressed'],
        0x02: [0x2, 0x0, 0x0, 'Reset Button pressed'],
        0x03: [0x3, 0x0, 0x0, 'FRU latch open'],
        0x04: [0x4, 0x0, 0x0, 'FRU service request button ']},

    # Chip set
    0x19: {
        0x00: [0x0, 0x0, 0x0, 'Soft Power Control Failure '],
        0x01: [0x1, 0x0, 0x0, 'Thermal Trip'] },

    # Cable / Interconnect
    0x1B: {
        0x00: [0x0, 0x0, 0x0, 'Cable/Interconnect is connected'],
        0x01: [0x1, 0x0, 0x0, 'Configuration Error - Incorrect cable connected / Incorrect interconnection' ]},

    #System Boot / Restart Initiated
    0x1D: {
        0x00: [0x0, 0x0, 0x0, 'Initiated by power up'],
        0x01: [0x1, 0x0, 0x0, 'Initiated by hard reset'],
        0x02: [0x2, 0x0, 0x0, 'Initiated by warm reset'],
        0x03: [0x3, 0x0, 0x0, 'User requested PXE boot'],
        0x04: [0x4, 0x0, 0x0, 'Automatic boot to diagnostic'],
        0x05: [0x5, 0x0, 0x0, 'OS / run-time software initiated hard reset'],
        0x06: [0x6, 0x0, 0x0, 'OS / run-time software initiated warm reset '],
        0x07: [0x7, 0x0, 0x0, 'System Restart'] },

    # boot error
    0x1E: {
        0x00: [0x0, 0x0, 0x0, 'No bootable media'],
        0x01: [0x1, 0x0, 0x0, 'Non-bootable diskette left in drive '],
        0x02: [0x2, 0x0, 0x0, 'PXE Server not found'],
        0x03: [0x3, 0x0, 0x0, 'Invalid boot sector'],
        0x04: [0x4, 0x0, 0x0, 'Timeout waiting for user selection of boot source']},

    # OS boot
    0x1F: {
        0x00: [0x0, 0x0, 0x0, 'A: boot completed'],
        0x01: [0x1, 0x0, 0x0, 'C: boot completed'],
        0x02: [0x2, 0x0, 0x0, 'PXE boot completed'],
        0x03: [0x3, 0x0, 0x0, 'Diagnostic boot completed'],
        0x04: [0x4, 0x0, 0x0, 'CD-ROM boot completed '],
        0x05: [0x5, 0x0, 0x0, 'ROM boot completed'],
        0x06: [0x6, 0x0, 0x0, 'boot completed - boot device not specified '] },

    # OS stop / shutdown
    0x20: {
        0x00: [0x0, 0x0, 0x0, 'Critical sStop during OS load / initialization'],
        0x01: [0x1, 0x0, 0x0, 'Run-time Critical Stop'],
        0x02: [0x2, 0x0, 0x0, 'OS Graceful Stop '],
        0x03: [0x3, 0x0, 0x0, 'OS Graceful Shutdown'],
        0x04: [0x4, 0x0, 0x0, 'Soft Shutdown initiated by PEF'] },

    # Slot / Connector
    0x21: {
        0x00: [0x0, 0x0, 0x0, 'Fault Status asserted'],
        0x01: [0x1, 0x0, 0x0, 'Identify Status asserted'],
        0x02: [0x2, 0x0, 0x0, 'Slot / Connector Device installed/attached'],
        0x03: [0x3, 0x0, 0x0, 'Slot / Connector Ready for Device Installation'],
        0x04: [0x4, 0x0, 0x0, 'Slot/Connector Ready for Device Removal'],
        0x05: [0x5, 0x0, 0x0, 'Slot Power is Off'],
        0x06: [0x6, 0x0, 0x0, 'Slot / Connector Device Removal Request'],
        0x07: [0x7, 0x0, 0x0, 'Interlock asserted'],
        0x08: [0x8, 0x0, 0x0, 'Slot is Disabled'],
        0x09: [0x9, 0x0, 0x0, 'Slot holds spare device'] },

    # System ACPI Power State
    0x22: {
        0x00: [0x0, 0x0, 0x0, 'S0 / G0 working'],
        0x01: [0x1, 0x0, 0x0, 'S1 sleeping with system h/w & processor context maintained'],
        0x02: [0x2, 0x0, 0x0, 'S2 sleeping, processor context lost'],
        0x03: [0x3, 0x0, 0x0, 'S3 sleeping, processor & h/w context lost, memory retained.'],
        0x04: [0x4, 0x0, 0x0, 'S4 non-volatile sleep / suspend-to disk'],
        0x05: [0x5, 0x0, 0x0, 'S5 / G2 soft-off'],
        0x06: [0x6, 0x0, 0x0, 'S4 / S5 soft-off, particular S4 / S5 state cannot be determined'],
        0x07: [0x7, 0x0, 0x0, 'G3 / Mechanical Off'],
        0x08: [0x8, 0x0, 0x0, 'Sleeping in an S1, S2, or S3 states'],
        0x09: [0x9, 0x0, 0x0, 'G1 sleeping (S1-S4 state cannot be determined)'],
        0x0A: [0xA, 0x0, 0x0, 'S5 entered by override'],
        0x0B: [0xB, 0x0, 0x0, 'Legacy ON state'],
        0x0C: [0xC, 0x0, 0x0, 'Legacy OFF state'],
        0x0D: [0xD, 0x0, 0x0, 'Unknown'] },

    # Watch dog 2
    0x23: {
        0x00: [0x0, 0x0, 0x0, 'Timer expired, status only'],
        0x01: [0x1, 0x0, 0x0, 'Hard Reset'],
        0x02: [0x2, 0x0, 0x0, 'Power Down'],
        0x03: [0x3, 0x0, 0x0, 'Power Cycle'],
        0x04: [0x5, 0x0, 0x0, 'Timer interrupt']},

    # Platform Alert
    0x24: {
        0x00: [0x0, 0x0, 0x0, 'platform generated page'],
        0x01: [0x1, 0x0, 0x0, 'platform generated LAN alert '],
        0x02: [0x2, 0x0, 0x0, 'Platform Event Trap generated, formatted per IPMI PET'],
        0x03: [0x3, 0x0, 0x0, 'platform generated SNMP trap, OEM format'] },

    # Entity Presence
    0x25: {
        0x00: [0x0, 0x0, 0x0, 'Entity Present'],
        0x01: [0x1, 0x0, 0x0, 'Entity Absent'],
        0x02: [0x2, 0x0, 0x0, 'Entity Disabled'] },

    # LAN
    0x27: {
        0x00: [0x0, 0x0, 0x0, 'LAN Heartbeat Lost '],
        0x01: [0x1, 0x0, 0x0, 'LAN Heartbeat'] },

    # Management Subsystem Health
    0x28: {
        0x00: [0x0, 0x0, 0x0, 'sensor access degraded or unavailable'],
        0x01: [0x1, 0x0, 0x0, 'controller access degraded or unavailable'],
        0x02: [0x2, 0x0, 0x0, 'management controller off-line'],
        0x03: [0x3, 0x0, 0x0, 'management controller unavailable'],
        0x04: [0x5, 0x0, 0x0, 'FRU failure'] },

    # Battery
    0x29: {
        0x00: [0x0, 0x0, 0x0, 'battery low (predictive failure)'],
        0x01: [0x1, 0x0, 0x0, 'battery failed'],
        0x02: [0x2, 0x0, 0x0, 'battery presence detected'] },

    # Session Audit
    0x2A: {
        0x00: [0x0, 0x0, 0x0, 'Session Activated'],
        0x01: [0x1, 0x0, 0x0, 'Session Deactivated'],
        0x02: [0x2, 0x0, 0x0, 'Invalid Username or Password '],
        0x03: [0x3, 0x0, 0x0, 'Invalid password disable A users access has been disabled due to a series of bad password attempts'] },

    # Version Change
    0x2B: {
        0x00: [0x0, 0x0, 0x0, 'Hardware change detected with associated Entity'],
        0x01: [0x1, 0x0, 0x0, 'Firmware or software change detected with associated Entity'],
        0x02: [0x2, 0x0, 0x0, 'Hardware incompatibility detected with associated Entity'],
        0x03: [0x3, 0x0, 0x0, 'Firmware or software incompatibility detected with associated Entity'],
        0x04: [0x4, 0x0, 0x0, 'Entity is of an invalid or unsupported hardware version'],
        0x05: [0x5, 0x0, 0x0, 'Entity contains an invalid or unsupported firmware or software version.'],
        0x06: [0x6, 0x0, 0x0, 'Hardware Change detected with associated Entity was successful'],
        0x07: [0x7, 0x0, 0x0, 'Software or F/W Change detected with associated Entity was successful'] },

    # FRU State
    0x2C: {
        0x00: [0x0, 0x0, 0x0, 'FRU Not Installed'],
        0x01: [0x1, 0x0, 0x0, 'FRU Inactive (in standby or hot spare state)'],
        0x02: [0x2, 0x0, 0x0, 'FRU Activation Requested'],
        0x03: [0x3, 0x0, 0x0, 'FRU Activation In Progress'],
        0x04: [0x4, 0x0, 0x0, 'FRU Active'],
        0x05: [0x5, 0x0, 0x0, 'FRU Deactivation Requested'],
        0x06: [0x6, 0x0, 0x0, 'FRU Deactivation In Progress'],
        0x07: [0x7, 0x0, 0x0, 'FRU Communication Lost'] }
}


# standard SEL
class SEL:
    def __init__(self):
        self.mc = 0x20
        self.record_id = 0
        self.record_type = 0x02
        self.ts_1 = 0
        self.ts_2 = 0
        self.ts_3 = 0
        self.ts_4 = 0
        self.gid_1 = 0
        self.gid_2 = 0
        self.evm_rev = 0x04
        self.sensor_type = 0
        self.sensor_num = 0
        self.event_dir = 0
        self.event_type = 0
        self.event_data_1 = 0
        self.event_data_2 = 0
        self.event_data_3 = 0

        self.min_event_id = 0
        self.max_event_id = 0

    def set_mc(self, mc):
        self.mc = mc

    def set_gid_1(self, gid_1):
        self.gid_1 = gid_1

    def set_gid_2(self, gid_2):
        self.gid_2 = gid_2

    def set_sensor_type(self, sensor_type):
        self.sensor_type = sensor_type

    def set_sensor_num(self, sensor_num):
        self.sensor_num = sensor_num

    def set_event_dir(self, event_dir):
        self.event_dir = event_dir

    def set_event_type(self, event_type):
        self.event_type = event_type

    def set_event_data_1(self, event_data_1):
        self.event_data_1 = event_data_1

    def set_event_data_2(self, event_data_2):
        self.event_data_2 = event_data_2

    def set_event_data_3(self, event_data_3):
        self.event_data_3 = event_data_3

    def check_event_type(self):
        if self.event_type == 0x6F:
            return True
        elif self.event_type >= 0x1 and self.event_type <= 0x0C:
            return True
        else:
            error_info = 'sensor num: {0}\n'.format(hex(self.sensor_num))
            error_info += 'event type {0} not in the sensor events.\
                    perhaps OEM defined'.format(hex(self.event_type))
            logger.error(error_info)
            msg_queue.put(error_info)
            return False

    # Standard sensor type range 0x1 - 0x2C.
    def check_sensor_type(self):
        if self.sensor_type >= 0x1 and self.sensor_type <= 0x2C:
            return True
        else:
            error_info = 'sensor num: {0}\n'.format(hex(self.sensor_num))
            error_info += 'sensor type {0} not exist in the stardard \
                    system\n'.format(hex(self.sensor_type))
            logger.error(error_info)
            msg_queue.put(error_info)
            return False

    # return the supported event list
    def get_event(self):
        if self.event_type >= 0x1 and self.event_type <= 0x0C:
            events = events_map[self.event_type]
            for event_id, description in events.items():
                info = '\tID: {0}\t{1}\n'.format(event_id, description)
                logger.info(info)
                msg_queue.put(info)
        elif self.event_type == 0x6F:
            events = sensor_specific_event_map[self.sensor_type]
            for event_id, event in events.items():
                info = '\tID: {0}\t{1}\n'.format(event_id, event[3])
                logger.info(info)
                msg_queue.put(info)
        else:
            error_info = 'sensor num: {0} event type {1} not exist\n'.format(
                        hex(self.sensor_num), hex(self.event_type))
            logger.error(error_info)
            msg_queue.put(error_info)
        return True

    def set_event_data(self, event_id):
        # check if sensor specific event
        if self.event_type >= 0x1 and self.event_type <= 0x0C:
            events = events_map[self.event_type]
            if event_id not in events:
                error_info = 'event id {0} not in the sensor event\n'.format(event_id)
                error_info += 'sensor num: {0} sensor type: {1} event type: {2}\n'.format( \
                            hex(self.sensor_num), hex(self.sensor_type), hex(self.event_type))
                logger.info(error_info)
                msg_queue.put(error_info)
                return False
            self.event_data_1 = event_id
            self.event_data_2 = 0
            self.event_data_3 = 0
        elif self.event_type == 0x6F:
            events = sensor_specific_event_map[self.sensor_type]
            if event_id not in events:
                error_info = 'event id {0} not in the sensor specific event\n'.format(event_id)
                error_info += 'sensor num: {0} sensor type: {1} event type: {2}\n'.format( \
                            hex(self.sensor_num), hex(self.sensor_type), hex(self.event_type))
                logger.info(error_info)
                msg_queue.put(error_info)
                return False
            self.event_data_1 = events[event_id][0]
            self.event_data_2 = events[event_id][1]
            self.event_data_3 = events[event_id][2]
        else:
            error_info = 'event type {0} not exist\n'.format(self.event_type)
            error_info += 'sensor num: {0}\n'.format(self.sensor_num)
            msg_queue.put(error_info)
            logger.error(error_info)
            return False
        return True

    # send SEL to IPMI simulator
    def send_event(self):
        command = 'sel_add ' + hex(self.mc) + ' ' + hex(self.record_type) + ' ' \
              + hex(self.ts_1) + ' ' + hex(self.ts_2) + ' ' + hex(self.ts_3) + ' ' + hex(self.ts_4) + ' ' \
              + hex(self.gid_1) + ' ' + hex(self.gid_2) + ' ' + hex(self.evm_rev) + ' ' \
              + hex(self.sensor_type) + ' ' + hex(self.sensor_num) + ' ' + hex((self.event_dir << 7)| self.event_type) + ' ' \
              + hex(self.event_data_1) + ' ' + hex(self.event_data_2) + ' ' + hex(self.event_data_3) + '\n'
        logger.info(command)
        send_ipmi_sim_command(command)


# OEM SEL Record - Type C0h-DFh
class OEM_SEL_C0_DF:
    def __init__(self):
        self.mc = 0x20
        self.record_id = 0
        self.record_type = 0
        self.ts_1 = 0
        self.ts_2 = 0
        self.ts_3 = 0
        self.ts_4 = 0
        self.mfg_id_1 = 0
        self.mfg_id_2 = 0

        # byte 11 - byte 16
        self.oem_defined = []

    def set_oem_defined_bytes(self, elements):
        for element in elements:
            self.oem_defined.append(element)

    def send_event(self, sel):
        command = 'sel_add ' + hex(self.mc) + ' ' + hex(self.record_type) + ' ' \
                + hex(self.ts_1) + ' ' + hex(self.ts_2) + ' ' + hex(self.ts_3) + ' ' + hex(self.ts_4) + ' ' \
                + hex(self.mfg_id_1) + ' ' + hex(self.mfg_id_2) + ' ' + hex(self.mfg_id_3) + ' ' \
                + ' '.join([hex(x) for x in self.oem_defined]) + '\n'

        logger.info(command)
        send_ipmi_sim_command(command)


# OEM SEL Record - Type E0h-FFh
class OEM_SEL_E0_FF:
    def __init__(self):
        self.mc = 0x20
        # two bytes record ID
        self.record_id = 0

        self.record_type = 0
        # byte 4 - byte 16
        self.oem_defined = []

    def set_oem_defined_bytes(self, elements):
        for element in elements:
            self.oem_defined.append(element)

    def send_event(self, sel):
        command = 'sel_add ' + hex(self.mc) + ' ' + hex(self.record_type) + ' ' \
                + ' '.join([hex(x) for x in self.oem_defined]) + '\n'
        logger.info(command)
        send_ipmi_sim_command(command)
