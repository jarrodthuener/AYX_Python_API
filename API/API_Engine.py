"""
AyxPlugin (required) has-a IncomingInterface (optional).
Although defining IncomingInterface is optional, the interface methods are needed if an upstream tool exists.
"""
import AlteryxPythonSDK as Sdk
import xml.etree.ElementTree as Et
import requests
import json


class AyxPlugin:
    """
    Implements the plugin interface methods, to be utilized by the Alteryx engine to communicate with a plugin.
    Prefixed with "pi", the Alteryx engine will expect the below five interface methods to be defined.
    """

    def __init__(self, n_tool_id: int, alteryx_engine: object, output_anchor_mgr: object):
        """
        Constructor is called whenever the Alteryx engine wants to instantiate an instance of this plugin.
        :param n_tool_id: The assigned unique identification for a tool instance.
        :param alteryx_engine: Provides an interface into the Alteryx engine.
        :param output_anchor_mgr: A helper that wraps the outgoing connections for a plugin.
        """

        # Default properties
        self.n_tool_id = n_tool_id
        self.alteryx_engine = alteryx_engine
        self.output_anchor_mgr = output_anchor_mgr

        # Custom properties
        self.Method = "Method"
        self.data_type = Sdk.FieldType.v_wstring
        self.data_size = 20
        self.URL = "URL"
        self.status = "Status"
        #self.data_type = Sdk.FieldType.v_wstring
        #self.data_size = 20
        self.response = "Response"
        #self.data_type = Sdk.FieldType.v_wstring
        #self.data_size = 50000


    def pi_init(self, str_xml: str):
        """
        Handles building out the sort info, to pass into pre_sort() later on, from the user configuration.
        Called when the Alteryx engine is ready to provide the tool configuration from the GUI.
        :param str_xml: The raw XML from the GUI.
        """
####### Why is the below code not working?
        if Et.fromstring(str_xml).find('URL') is not None:
            self.url = Et.fromstring(str_xml).find('URL').text
        else:
            self.alteryx_engine.output_message(self.n_tool_id, Sdk.EngineMessageType.error, 'Please select field containing the URL')

        if Et.fromstring(str_xml).find('Method') is not None:
            self.method = Et.fromstring(str_xml).find('Method').text
        else:
            self.alteryx_engine.output_message(self.n_tool_id, Sdk.EngineMessageType.error, 'Please select field containing the Method')
        
        self.header = Et.fromstring(str_xml).find('Headers').text if 'Headers' in str_xml else None
        self.body = Et.fromstring(str_xml).find('Body').text if 'Body' in str_xml else None
        
        #self.alteryx_engine.output_message(self.n_tool_id, Sdk.EngineMessageType.info, self.field_selection)

        self.output_anchor = self.output_anchor_mgr.get_output_anchor('Output')  # Getting the output anchor from the XML file.


    def pi_add_incoming_connection(self, str_type: str, str_name: str) -> object:
        """
        The IncomingInterface objects are instantiated here, one object per incoming connection, also pre_sort() is called here.
        Called when the Alteryx engine is attempting to add an incoming data connection.
        :param str_type: The name of the input connection anchor, defined in the Config.xml file.
        :param str_name: The name of the wire, defined by the workflow author.
        :return: The IncomingInterface object(s).
        """

        self.single_input = IncomingInterface(self)
        return self.single_input

    def pi_add_outgoing_connection(self, str_name: str) -> bool:
        """
        Called when the Alteryx engine is attempting to add an outgoing data connection.
        :param str_name: The name of the output connection anchor, defined in the Config.xml file.
        :return: True signifies that the connection is accepted.
        """

        return True
    def pi_push_all_records(self, n_record_limit: int) -> bool:
        """
        Called when a tool has no incoming data connection.
        :param n_record_limit: Set it to <0 for no limit, 0 for no records, and >0 to specify the number of records.
        :return: True for success, False for failure.
        """
        # Save a reference to the RecordInfo passed into this function in the global namespace, so we can access it later.
        record_info_out = Sdk.RecordInfo(self.alteryx_engine)


        # Adds the new field to the record.
        self.response = record_info_out.add_field(self.response, self.string)
         # Lets the downstream tools know what the outgoing record metadata will look like, based on record_info_out.
        self.output_anchor.init(record_info_out)       


        # Creating a new, empty record creator based on record_info_out's record layout.
        record_creator = record_info_out.construct_record_creator()

        previous_inc_value = self.starting_value
        
        self.alteryx_engine.output_message(self.n_tool_id, Sdk.EngineMessageType.error, self.xmsg('Missing Incoming Connection'))
        return False

    def pi_close(self, b_has_errors: bool):
        """
        Called after all records have been processed..
        :param b_has_errors: Set to true to not do the final processing.
        """

        self.output_anchor.assert_close()  # Checks whether connections were properly closed.

class IncomingInterface:
    """
    This optional class is returned by pi_add_incoming_connection, and it implements the incoming interface methods, to
    be utilized by the Alteryx engine to communicate with a plugin when processing an incoming connection.
    Prefixed with "ii", the Alteryx engine will expect the below four interface methods to be defined.
    """


    def __init__(self, parent: object):
        """
        Constructor for IncomingInterface.
        :param parent: AyxPlugin
        """

        # Default properties
        self.parent = parent

        # Custom properties
        self.record_copier = None
        self.record_creator = None

    def ii_init(self, record_info_in: object) -> bool:
        """
        Called to report changes of the incoming connection's record metadata to the Alteryx engine.
        :param record_info_in: A RecordInfo object for the incoming connection's fields.
        :return: True for success, otherwise False.
        """

        # Returns a new, empty RecordCreator object that is identical to record_info_in.
        record_info_out = record_info_in.clone()

        # Adds field to record with specified name and output type.
        #record_info_out.add_field(self.parent.out_name, self.parent.out_type, self.parent.out_size)

        record_info_out.add_field(self.parent.status,self.parent.data_type, self.parent.data_size)
        record_info_out.add_field(self.parent.response,self.parent.data_type_double)


        # Lets the downstream tools know what the outgoing record metadata will look like, based on record_info_out.
        self.parent.output_anchor.init(record_info_out)

        # Creating a new, empty record creator based on record_info_out's record layout.
        self.record_creator = record_info_out.construct_record_creator()

        # Instantiate a new instance of the RecordCopier class.
        self.record_copier = Sdk.RecordCopier(record_info_out, record_info_in)

        # Map each column of the input to where we want in the output.
        for index in range(record_info_in.num_fields):
            # Adding a field index mapping.
            self.record_copier.add(index, index)

        # Let record copier know that all field mappings have been added.
        self.record_copier.done_adding()

        # Grab the index of our new field in the record, so we don't have to do a string lookup on every push_record.
        #self.parent.out_field = record_info_out[record_info_out.get_field_num(self.parent.out_name)]

        self.parent.status = record_info_out[record_info_out.get_field_num(self.parent.status)]
        self.parent.response = record_info_out[record_info_out.get_field_num(self.parent.response)]


        # Grab the index of our input field in the record, so we don't have to do a string lookup on every push_record.
        self.parent.input_field = record_info_out[record_info_out.get_field_num(self.parent.field_selection)]

        return True

    def ii_push_record(self, in_record: object) -> bool:
        """
        Responsible for pushing records out
        Called when an input record is being sent to the plugin.
        :param in_record: The data for the incoming record.
        :return: False if method calling limit (record_cnt) is hit.
        """
        # Copy the data from the incoming record into the outgoing record.
        self.record_creator.reset()
        self.record_copier.copy(self.record_creator, in_record)
##########






# read in the data
input = Alteryx.read('#1')


# Create MakeCall function to handle the combination of the status and response

    r = requests.request(method,url,header,body)
    response = r.text
    status = str(r.status_code)
    


    
  





##############  
        #Write Outputs to correct Fields
        out_record = self.record_creator.finalize_record()

        # Push the record downstream and quit if there's a downstream error.
        if not self.parent.output_anchor.push_record(out_record):
            return False

        return True
    def ii_update_progress(self, d_percent: float):
        """
        Called by the upstream tool to report what percentage of records have been pushed.
        :param d_percent: Value between 0.0 and 1.0.
        """
 
        self.parent.alteryx_engine.output_tool_progress(self.parent.n_tool_id, d_percent)  # Inform the Alteryx engine of the tool's progress.
        self.parent.output_anchor.update_progress(d_percent)  # Inform the downstream tool of this tool's progress.
 
    def ii_close(self):
        """
        Called when the incoming connection has finished passing all of its records.
        """
 
        self.parent.output_anchor.output_record_count(True)  # True: Let Alteryx engine know that all records have been sent downstream.
        self.parent.output_anchor.close()  # Close outgoing connections.