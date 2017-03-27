from flask_restplus import Namespace, Resource
from infrasim.redfishsim.core.model_factory import ModelFactory
from infrasim.redfishsim.schemas.redfish_1_0_0.model import fake_import_driver

api = Namespace('redfish_sim_1_0_0', 'Redfish simulator 1.0.0 of InfraSIM')
redfish_model = ModelFactory()
fake_import_driver(redfish_model, None, api)


@api.route('/ServiceRoot')
class ServiceRoot(Resource):
    """
    ServiceRoot provides a collection of all resources that are manageable
    by OnRack.  All components discovered by OnRack may be accessed either
    directly or indirectly through this object.
    """
    @api.marshal_with(redfish_model.ServiceRoot_1_0_0_ServiceRoot)
    def get(self):
        """retrieve list of root-level resources for an OnRack appliance"""
        return {
            "Tasks": None,
            "Systems": None,
            "Description": None,
            "AccountService": None,
            "UUID": None,
            "Registries": None,
            "Name": "ServiceRoot hello world",
            "SessionService": None,
            "EventService": None,
            "Oem": {},
            "Id": None,
            "Links": None,
            "RedfishVersion": "",
            "@odata.type": "Simulated OData type",
            "JsonSchemas": None,
            "@odata.id": "Simulated OData ID",
            "@odata.context": "Simulated OData context",
            "Chassis": None,
            "Managers": None
        }


@api.route('/Chassis')
class ChassisCollection(Resource):
    """
    This object represent a collection of chassis discovered by OnRack. The
    unique identifiers represents the properties for physical components of
    the system.
    """
    @api.marshal_with(redfish_model.ChassisCollection_ChassisCollection)
    def get(self):
        """retrieve list of physical components discovered by OnRack"""
        return {
            "Name": "ChassisCollection hello world",
            "Members": [],
            "Description": "This is a simulated resource of ChassisCollection_ChassisCollection",
            "Oem": {},
            "@odata.context": "Simulated OData context",
            "@odata.type": "Simulated OData type",
            "Members@odata.navigationLink": "Simulated OData navigation link",
            "@odata.id": "Simulated OData ID",
            "Members@odata.count": "Simulated member count"
        }


@api.route('/Systems')
class SystemsCollection(Resource):
    """
    This object represent a collection of computer systems discovered by
    OnRack. The unique identifiers represents a computer system and
    components such as memory, cpu and storage.
    """
    @api.marshal_with(redfish_model.ComputerSystemCollection_ComputerSystemCollection)
    def get(self):
        """retrieve list of computer systems (physical and virtual) discovered by OnRack"""
        return {
            "Description": "This is a simulated resource of ComputerSystemCollection_ComputerSystemCollection",
            "Oem": {},
            "Members": [],
            "@odata.type": "Simulated OData type",
            "Name": "SystemsCollection hello world",
            "Members@odata.navigationLink": "Simulated OData navigation link",
            "Members@odata.count": "Simulated member count",
            "@odata.context": "Simulated OData context",
            "@odata.id": "Simulated OData ID"
        }

@api.route('/Managers')
class ManagerCollection(Resource):
    """
    This object represent a collection of management server discovered by OnRack. The
    unique identifiers represents the properties for physical components of
    the system.
    """
    @api.marshal_with(redfish_model.ManagerCollection_ManagerCollection)
    def get(self):
        """retrieve list of management servers discovered by OnRack"""
        return {
            "Description": "This is a simulated resource of ManagerCollection_ManagerCollection",
            "Members@odata.navigationLink": "Simulated OData navigation link",
            "Name": "ManagerCollection hello world",
            "@odata.type": "Simulated OData type",
            "Oem": {},
            "@odata.id": "Simulated OData ID",
            "Members@odata.count": "Simulated member count",
            "Members": [],
            "@odata.context": "Simulated OData context",
        }
