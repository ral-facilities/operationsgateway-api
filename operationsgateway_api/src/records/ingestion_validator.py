import logging
from datetime import datetime

from operationsgateway_api.src.exceptions import RejectFile, RejectRecord
from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.models import RecordModel
from operationsgateway_api.src.constants import DATA_DATETIME_FORMAT


log = logging.getLogger()


    
async def get_manifest():
    return await ChannelManifest.get_most_recent_manifest()

class FileChecks:
    def __init__(self, ingested_record: RecordModel):
        self.ingested_record = ingested_record

    def epac_data_version_checks(self):
        ingested_metadata = (self.ingested_record).metadata
        if hasattr(ingested_metadata, "epac_ops_data_version") and ingested_metadata.epac_ops_data_version is not None:     #is the has attribute needed?
            epac_number = ingested_metadata.epac_ops_data_version
            if type(ingested_metadata.epac_ops_data_version) != str:
                raise RejectFile("epac_ops_data_version has wrong datatype. Should be string")
            else:
                epac_numbers = epac_number.split(".")
                if epac_numbers[0] != "1":
                    raise RejectFile("epac_ops_data_version major version was not 1")
                if int(epac_numbers[1]) > 0:
                    return("File minor version number too high (expected 0)")
        else:
            raise RejectFile("epac_ops_data_version does not exist")
        # a RecordMetadataModel is already returned when 
        # epac_ops_data_version does not exist

class RecordChecks:
    def __init__(self, ingested_record: RecordModel):
        self.ingested_record = ingested_record

    def active_area_checks(self):
        ingested_metadata = (self.ingested_record).metadata
        if hasattr(ingested_metadata, "active_area") and ingested_metadata.active_area is not None:     #is the has attribute needed?
            if type(ingested_metadata.active_area) != str:
                raise RejectRecord("active_area has wrong datatype. Expected string")
        else:
            raise RejectRecord("active_area is missing")

    def optional_metadata_checks(self):
        ingested_metadata = (self.ingested_record).metadata
        if hasattr(ingested_metadata, "active_experiment") and ingested_metadata.active_experiment is not None:     #is the has attribute needed?
            if type(ingested_metadata.active_experiment) != str:
                raise RejectRecord("active_experiment has wrong datatype. Expected string")
        if hasattr(ingested_metadata, "shotnum") and ingested_metadata.shotnum is not None:     #is the has attribute needed?
            if type(ingested_metadata.shotnum) != int:
                raise RejectRecord("shotnum has wrong datatype. Expected integer")
        

class ChannelChecks:
    def __init__(self, ingested_record: RecordModel, ingested_waveform, ingested_image):
        self.ingested_record = ingested_record
        self.ingested_waveform = ingested_waveform
        self.ingested_image = ingested_image

    async def channel_dtype_checks(self):
        ingested_channels = (self.ingested_record).channels
        manifest_channels = (await get_manifest()).channels

        supported_values = [
            "scalar",
            "image",
            "rgb-image",
            "waveform",
        ]

        rejected_channels = []

        for key, value in ingested_channels.items():
            if hasattr(value.metadata, "channel_dtype"):
                if manifest_channels.type != value.metadata.channel_dtype or value.metadata.channel_dtype not in supported_values:
                    reason = [key, "channel_dtype has wrong data type or its value is unsupported"]
                    rejected_channels.append[reason]
            else:
                reason = [key, "channel_dtype attribute is missing"]
                rejected_channels.append[reason]
        return rejected_channels
    
    
    def required_attribute_missing(self):
        ingested_channels = (self.ingested_record).channels
        
        rejected_channels = []
        
        for key, value in ingested_channels:
            if hasattr(value, "metadata"):
                pass
            else:
                rejected_channels.append[key, "metadata attribute is missing"]
            
            if value.metadata.channel_dtype == "scalar":
                if hasattr(value, "data"):
                    pass
                else:
                    rejected_channels.append[key, "data attribute is missing"]
            
            if value.metadata.channel_dtype == "image":
                if hasattr(value, "image_path"):
                    pass
                    # path, data
                else:
                    rejected_channels.append[key, "image_path attribute is missing"]
            if value.metadata.channel_dtype == "waveform":
                pass
                # waveform_id, id_, x, y
                
        # reject channel
        # channel specs are higher on the page


    def optional_attribute_wrong_dtype(self):
        # reject channel OR ignore attribute and warn
        pass

    def required_dataset_missing_wrong_dtype_shape(self):
        # reject channel
        pass

    def unexpected_group_or_dataset_in_channel_group(self):
        # reject channel
        pass

    async def channel_name_check(self):

        ingested_channels = (self.ingested_record).channels
        manifest = (await get_manifest()).channels

        rejected_channels = []
        
        for key in list(ingested_channels.keys()):
            if key not in manifest:
                reason = [key, "Channel name is not recognised (does not appear in manifest)"]
                rejected_channels.append[reason]
                # reject on import?
        return rejected_channels
                
    async def channel_checks(self):
        # this will run all channel checks and return the big dictionary of the
        # channels that passed and which failed and why
        return

class PartialImportChecks:
    # checked in certain circumstances
    def __init__(self, ingested_record: RecordModel, stored_record: RecordModel):
        self.ingested_record = ingested_record
        self.stored_record = stored_record

    def metadata_checks(self):
        ingested_metadata = (self.ingested_record).metadata
        stored_metadata = (self.stored_record).metadata

        time_match = ingested_metadata.timestamp == stored_metadata.timestamp
        epac_match = (
            ingested_metadata.epac_ops_data_version
            == stored_metadata.epac_ops_data_version
        )
        shot_match = ingested_metadata.shotnum == stored_metadata.shotnum
        area_match = ingested_metadata.active_area == stored_metadata.active_area
        experiment_match = ingested_metadata.active_experiment == stored_metadata.active_experiment

        if ingested_metadata == stored_metadata:
            log.info("record metadata matches existing record perfectly")
            return("accept record and merge")

        elif time_match and not epac_match and not shot_match and not area_match and not experiment_match:
            raise RejectRecord("timestamp is matches, other metadata does not")

        elif shot_match and not time_match and not epac_match and not area_match and not experiment_match:
            raise RejectRecord("shotnum is matches, other metadata does not")

        elif not time_match and not shot_match:
            return("accept as a new record")

    def channel_checks(self):
        ingested_channels = (self.ingested_record).channels
        stored_channels = (self.stored_record).channels

        rejected_channels = []

        for key in list(ingested_channels.keys()):
            if key in stored_channels:
                reason = [key, "Channel is already present in existing record"]
                rejected_channels.append[reason]
                
        return rejected_channels
        # make look all fancy like the other channel rejects in the dict


"""
{
    "accepted_channels": ["channel1", "channel2"],
    "rejected_channels": {
        "channel3": ["reason1", "reason2"],
        "channel4": ["reason1", "reason2"]
    },
}

^ good template for the warning system and stuff could use ^

(template has been duplicated make sure to edit both)

"""





"""
Record e.g:
id_='20220407142816' 
metadata=RecordMetadataModel(epac_ops_data_version='1.0', shotnum=366272, timestamp=datetime.datetime(2022, 4, 7, 14, 28, 16)) 
channels={
'GEM_SHOT_NUM_VALUE': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=366272.0), 
'GEM_SHOT_SOURCE_STRING': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data='EX'), 
'GEM_SHOT_TYPE_STRING': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data='FP'), 
'GEM_WP_POS_VALUE': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='ms'), data=45.0), 
'N_COMP_CALCULATEDE_VALUE': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='mm'), data=10.84), 
'N_COMP_FF_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='mg'), data=-8895000.0), 
'N_COMP_FF_IMAGE': ImageChannelModel(metadata=ImageChannelMetadataModel(channel_dtype='image', exposure_time_s=0.001, gain=5.5, x_pixel_size=441.0, x_pixel_units='µm', y_pixel_size=441.0, y_pixel_units='µm'), image_path='20220407142816/N_COMP_FF_IMAGE.png', thumbnail=None), 
'N_COMP_FF_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='µm'), data=8895000.0), 
'N_COMP_FF_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='mm'), data=330.523), 
'N_COMP_FF_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='mm'), data=243.771), 
'N_COMP_THROUGHPUTE_VALUE': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='cm'), data=74.0), 
'TA3_SHOT_NUM_VALUE': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=217343.0), 
'Type': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data='GS')
} 


Existant record e.g:
id_='20220407142816' 
metadata=RecordMetadataModel(epac_ops_data_version='1.0', shotnum=366272, timestamp=datetime.datetime(2022, 4, 7, 14, 28, 16)) 
channels={
'GEM_SHOT_NUM_VALUE': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=366272.0), 
'GEM_SHOT_SOURCE_STRING': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data='EX'), 
'GEM_SHOT_TYPE_STRING': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data='FP'), 
'GEM_WP_POS_VALUE': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='ms'), data=45.0), 
'N_COMP_CALCULATEDE_VALUE': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='mm'), data=10.84), 
'N_COMP_FF_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='mg'), data=-8895000.0), 
'N_COMP_FF_IMAGE': ImageChannelModel(metadata=ImageChannelMetadataModel(channel_dtype='image', exposure_time_s=0.001, gain=5.5, x_pixel_size=441.0, x_pixel_units='µm', y_pixel_size=441.0, y_pixel_units='µm'), image_path='20220407142816/N_COMP_FF_IMAGE.png', thumbnail='iVBORw0KGgoAAAANSUhEUgAAADIAAAAmCAAAAACjE5fgAAACGklEQVR4nH2VvXLUQBCE+5vVgU0VFEVAAjkPwPu/CykJCQa7fN5pgv3R3xkFdyrN9nRv92jFovNF/zeST9W4gZjLuFU8QxAwANyCnXWN9bjfHaXdFNbVWRKcePaQWUcAbsoOqOVVhMwwDG/VNRb25A2Kms3H/SxdN5aQ3HhAtOV0x1kDGsIaaLgKpAQpt8VsmAZkJICwSoSxbJEcda0sXTS2Ikq4tuYxKjccW5WDq4VRUCX5EOaE0HeEIiwRJSG49udNHhbe52JClt4ihVWKVTejzJZlUIOMyqVkXF6eCzWL5Zwme0I6og9iQeVy+fDgyOpLJa2QhTGyiC61kdqWXTPef/327m55Uam1zDHqwW1ZmnHkUuvH759///jjix4zzd7oUB/CucUwfnp++Huvq7gm6fYeeDZdNl5IEDiW+y+f9POXM5+Uck2PbCyJZQuQVDBxf3cpDzV4fHN9tpLqmc4OgtWSlIoKqo7r4sxm88qyaE68kQ0mXCVRqZnVFjnNGSwtqTGXRMkEFacTOZFlVgdihD6b2FW0QgpZHjVvBsaMl0UmhLBtpahjTjbDPIWtQYGG/Nyt3bJoE6/Xpths3vlxEyMR94WW7RwReJo1fJ0QW7K1HjNWP8XWPA7Cxs7WD8Q6Uu1n3dPxGPduqnvvLeB8jK/WdVHzlH0Fsq1hu+9yf9367rUre7wnyEGYZ1Pvbfovizedz+sl/QPRNh7zEfLxpAAAAABJRU5ErkJggg=='), 
'N_COMP_FF_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='µm'), data=8895000.0), 
'N_COMP_FF_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='mm'), data=330.523), 
'N_COMP_FF_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='mm'), data=243.771), 
'N_COMP_THROUGHPUTE_VALUE': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='cm'), data=74.0), 
'TA3_SHOT_NUM_VALUE': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=217343.0), 
'Type': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data='GS'), 
'N_COMP_NF_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=-608.362), 
'N_COMP_NF_IMAGE': ImageChannelModel(metadata=ImageChannelMetadataModel(channel_dtype='image', exposure_time_s=0.001, gain=5.0, x_pixel_size=441.0, x_pixel_units='µm', y_pixel_size=441.0, y_pixel_units='µm'), image_path='20220407142816/N_COMP_NF_IMAGE.png', thumbnail='iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAAAAAA7VNdtAAAEuklEQVR4nJ2WyZIkORGGf3eXFJERmZW1YG3Q0IbBMPP+D8N5DgOYwUzTtWYski8cMjuprOk6gB8lfebbL7mI8coIAJiFCQC5e4RH4MIivSW4iGSRFuERanB/AxHxBYA8lpySrIBS6NKMws3xGjojBADo77apJ2WBqluta3PSZheOXiMk+9tB+p2iJVtpXeGqtVlrzV4x6RXBd39Mpbqm4lMTKqTGXZ40HwKGc3DpVVjXf972Uvm566y2RQPEBsnOGQiPCy8EALT7/jaJhF37C1mhafaAWy6rb4Q8guJtYOW7G8rJtpMRaaO0H+7nIHdOyMk1zsw5MP7d70NXoipm1XPNqtIrFasbR+7U3U9MOqWO8RMPNFCbjNjV0Mw4MTvatOHomp2Llk5E+f5PUpaZVJVaUkqNC5sLIj8ldy6tGR3dpFMPt3f/7oRiJniIQQPMCl4J8puG1SjE9SJ9+TgAFDLU6olYRrYMJht01oN0lNCFnVI5apa2fyGHQbMkitj0PRJZbsvTZ08iq4Cz0DFtP3rhT7t75ZyEY4HUwybISELFwTmiOC3n7nsCQNR/J7J7rHeLVUoNWcQbJ93VrhsicTPRZH7Ryg+fKKbnPBP3vTxWeNHSpE9frtzH2WguKcIBgAIMEMlH1G747cfB0JSGHOajqS5Ed37QpgDB7avIGADKzbK2tL/GX3nT74fxdhAZB26HjY43D1MnnKD2Wsk0jCyBlPY/+EjuhceJ87DkxEQuRFSyXiqZ9rtioI79k6qT6xBht041p+alpkDHcZJLHBG+2WzHpfnPY6SuyDIGqj/bnM2zHDqIUelOCAUSABG/8dXSwH2rV3cRqfzzYb1CY1/X5xg7zu56EVhs2meu2yRPtUZfZ08yxmLOpQ7sD5v+cSeLXt59XZzvhvmBulnvh9X9PjhDGxl0g362SerXglEkIKK+rLYppVg1FLqC1Y7cNfJ2NX3ueC3r6mcvDIDFHuLz+q+/2US26iJipuvjMq23m63uM3a9/vclowRAX7r0YT9fFXu8qjY9Fmkyr4nRflGnEvOa3B0AxIOQANg9d//Y9vH8cTtd80PGyiti0az3N+mKoaRLAxj44ZdDCwYQh9oOP1kZnw5eOvHapOu4esk7c1+fQlA18IcuvvR3XUpBiOXAy/IUJTi+2GIzu7WpjRo5YzJIW2az27s4/EyZj8OizsNL4INgkbT/rPmwXm8Wt8Uzu7q9xNQcy4+x90mPucCWF6XnrVKA12GaFeGyWaSzBYj5Rc2CpgMeMhBHLzGnkJe/b/fb1D9NDPJHFBZTjsfkdY7wAIhgBEJCEKArdwuPPu8rNLDOOSHX50xUDu3Q4ni/ghBHWQYhKnJOLzqycNdMBqQvMs0lyJe2eLP2tZMn8QdB6YBa+2W+7mZe5l19XshIjeqqTVWPOg7gPCsJnLvcbUoeO1KvPTWqBkOsk9VVmwcQp6FyGnwETlm6PkcaaBnBaO7VV3fXWjX86OPIfEUATiVn2XXcQjLUbVka1Fw1AueXj87j9chLJhGQi8MjzCLidOnfmchAgOhYzjivXZ7/xlfhG/bmQ4J0sfUt6i2B9KttOpXzV0fP0fB7O+/a/078X8i7Ib9r/wGHbipq3c4V4gAAAABJRU5ErkJggg=='), 
'N_COMP_NF_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=118300000.0), 
'N_COMP_NF_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='mm'), data=236.857), 
'N_COMP_NF_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='mm'), data=229.859), 
'N_COMP_SPEC_TRACE': WaveformChannelModel(metadata=WaveformChannelMetadataModel(channel_dtype='waveform', x_units='s', y_units='kJ'), 
thumbnail='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', waveform_id='20220407142816_N_COMP_SPEC_TRACE'), 
'N_LEG1_GREEN_NF_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=20.026), 
'N_LEG1_GREEN_NF_IMAGE': ImageChannelModel(metadata=ImageChannelMetadataModel(channel_dtype='image', exposure_time_s=0.055, gain=7.89, x_pixel_size=300.0, x_pixel_units='µm', y_pixel_size=300.0, y_pixel_units='µm'), image_path='20220407142816/N_LEG1_GREEN_NF_IMAGE.png', thumbnail='iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAAAAAA7VNdtAAAEqElEQVR4nNWV224ktxGG/zqQ7OmZkTS7G3udBDBy4bz/i+QmgAHDF3HgsyJodZpDN8mqyoVGo5GDJNcm2ESjwa9/1olFGQBAL8vLcz7i7cNx+nqkiE4/OXs9oxRBAI7raRCEZaG1d3d3CjzPAAA9232EQSTrVVFaJI2HynY9tQAACgoAlF6E6TiJ+erzzaJjHvIohjnNvzxe7/35XIGgdGY8gQD6cDV+zKm+LzRoWY034bj77vvb7SECCIT+xjtSFnm8HBfrskytNZsbj7x+//HLH++/uUMAAX1jO8nVVxd9XH54P8vNv6LMdUqUNquL/K6V8W/3AdDzwY7RIEqbPy/L8t24bDf3u+EHpQgdasjqjwPu+PuvH+PFlmM8SNZfbHSzKbr/5c4eFj5nlzSIWvXNxsw+/f3B39rCwyLZ6l2e9tdPhrKDRPReZVhc9r1dUlz+9estQHpyF+v6TxdlQYP/vI1wB4BEC3EjXWjn9fIW335nrypEJBcFw2H9M/aGGsQKKYmNBvaGjnl9tfvy5uHZYyAAQWUAeMKWe/QuIqLK3iOqjtQzZl9z+mJrfMo44qEwprhFJ0CVCRytu1niyYMG3KdL/XwAn1Q4F2WqoSzElJQ1UYSHFELsaT6keh+8XhGf/KWjBlBr18RgAsObuZE3a+4iLvTYy3IjJ4RkNZoWcgGHKCI4lFUpehWWCXaQ6YHKRvlUOVa5MCXmEpqYmYHqHu4sDPPZHPWT7y6yvpRKxOFxuWlz0kIwIkGQBtydZIa3UqYM27c8nEqMmGqDSF44q6kDQURuDGeK4J7tCbRjL6dQyqpYsU65NDM2Dga5tw4wWYRnj5qmrCF6zP1oT8sErygZUZ3gIFEzc0IECaGBZrfG/FovputKMw0BzjVcLExE3aDGRGGKbl7RZj1GnxCm++0hz545cg2lDjTmYPUwpogmaC28n2wJq+XhafaxshNEjQXMYHAgQB4g8+jW55dQBuJufFe9HvaVkyoLadCgeYB7JA4iE1Dvtb4mDNJP1yOmqW/7rL0bcVbPAxNCpTsh2IK8t1eEM8oqR43dUxzUmYQCxMQshSOjSmDBNNkrYvfbsSXaTvJYvYow0KxOTbmQEZGRq4bv/YQEWvnQl0t/ariv1itiGABPUjSoWGiKEtbms+sicPsXyLCYtgvskBKVnhKyeFhPjI7IPPeHHhqndhKffv1DK5d+2CXh2m0e2NxFOIgIcNba+86gZw3I/nFRF2XptYaW2cmmzGFsnqJWJgnrnyrAiDgxj/8se5QxC03b+YBSwoI84NMMsNb28OQIEpx1Ov24vBDfo01OYboeBNzEDJKE67z78QCABG+Y8bM1KLCvJGHGEppI08K19rn+9BT4j2ZhuxtJTJI6aFCDsyQlELett+ttIOiocqYj66skqZtxypSEKYJ656n220d/vvCOyCvDeZ2ysIFVS6RkXQ5zC7t97n3Aa/K/QD71oeQMy4AndJ952nt9rC+uPamcC1EahjAdi5YqPsW8nw92isU58goRK4WUnKSLtLY/2Fn03nosjliYgdjNdOI4ND8DfqvyVoxIyCLe7P9vyP8e/P+3/G6QfwOesNYOApsETgAAAABJRU5ErkJggg=='), 
'N_LEG1_GREEN_NF_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=44120000.0), 
'N_LEG1_GREEN_NF_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='µm'), data=374.788), 
'N_LEG1_GREEN_NF_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='µm'), data=208.576), 
'N_FLUOR_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=-205.752), 
'N_FLUOR_IMAGE': ImageChannelModel(metadata=ImageChannelMetadataModel(channel_dtype='image', exposure_time_s=0.105, gain=2.4214, x_pixel_size=250.0, x_pixel_units='µm', y_pixel_size=250.0, y_pixel_units='µm'), image_path='20220407142816/N_FLUOR_IMAGE.png', thumbnail='iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAAAAAA7VNdtAAAD+klEQVR4nJWW13rjOAyFcUCquKZO2dn3f7TZzTeZcYptWRIJnL2wbEtJtvFOIn8eAEIRVC4L8s+LIiKi/3JqQuB/IwMT/7NV5xMnFbwnALy7BxOVN3sUQgaGk62/Qyb3g+P30Lf7IhBABSIU+iAxgt6rAKo4W0S6cyr0DtFwBE6IKM0pgrNQnNqFoApAoYBQ3OkCuPnU/ZGmBoUihBhDVDW3nLK5KNx4PhdlFHyNCoRYVfWsrEK0Ph+aQ5fMXeXCxFGwNCo0lvXqarVe1DHKoX95ft7t2yRjZuS+BkWI9eLm7u7uZh4LlWxPj782m5ddJ660wYdRjoUAjbP1p69fbm6uhXSlzNeff3wv9bUT19M3uiCq0Fivv377dl9i23oyiXVVl1UsQHaEklMVKKDl4u63369sm7atmJH1fDavv8BSNhJq00+pCsT6+uuX9X5rzQ6eExy6vP9UXH3uUzIHQPCCQIFQLm/v1v3zpuv7sm9JJ592vC5vU9P0TqgJOEXq5fWi3T4+uaV9RzdQQg7d5zBbvzTJBBNfIKKxWi11+7hJlrtMEoQm/rS4nq2X287IsS8AoMVsEbcvPxtk6zMhRDCzYtfMUc3r2OOtClDWM9k+77K4iZkKIkzY6XZRllUR1I6ppSPDQq3M+77PnpLBMz0Rng6vKRRFDBj6wyhhoGqHJhmY3UiKGNRFPEMYFCJH/08IRQTuKYtKMgEEMFFCNXTJxHkukbEKFJSgLoRSYUKKKt0yLVNOpXjulhTmLDGIiICiQaWIAonKEEu4OYdSjkOjpdBzSlEkiMJFxSGMFUU1FgUt2cn+kWG01BdaJPEeQahq0KAx6HqZm7Y/ywxVSQotd10dVZ2BwaFCwMsyVLerPjedUab1QpKpaRblUg5JRRRQDUFnVbG+4/a1SXa8eIyIW7tfVotQaZMlRPVQFzKflau79mmzT6QcA31235XW71/r22JWlF0GCq3qEFcLucXz5qVJTh67WcTAuMNz81wul1LOD11OdVWiWNyXWj48/Nz1Rhn8j6cuRlfP3f6pkKv1ddsmqlblYlF5/vHH902TSfok+U8y7Sss3S9nMUkZUK6kOTz8+ePXrjcXP3UYnnofDSKp8dwfrm9WdRnU9KXZPzz+et73meImb1XEc5RMt3b3slktFyrZ9oft5nXXJiPdTnl5nD3D0qjQUJSzsq5LBVPbdocumZG003B6M8U0AqoaQ9QA0HO27E7yOGPGyJlBCBAFAAh4jBIpbpdy4YBcGFWFCIaxxdHsO56/IFPo+Ew5FsXFJiEo0DeEHDvUsTWQ5MUkERHKBZlSw2zjm78Ejtx/z7xfHEbSlDjl94cEPlI5KfEDuctVfwG6tXF4RCZixgAAAABJRU5ErkJggg=='), 
'N_FLUOR_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=23930000.0), 
'N_FLUOR_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=340.075), 
'N_FLUOR_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=276.965), 
'N_INP_NF_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=1.583), 
'N_INP_NF_IMAGE': ImageChannelModel(metadata=ImageChannelMetadataModel(channel_dtype='image', exposure_time_s=0.3141, gain=3.141, x_pixel_size=314.0, x_pixel_units='µm', y_pixel_size=314.0, y_pixel_units='µm'), image_path='20220407142816/N_INP_NF_IMAGE.png', thumbnail='iVBORw0KGgoAAAANSUhEUgAAADIAAAAxCAAAAAC9wKXDAAAESElEQVR4nG1WTZPcuhEDuklJu167Nqnk3fL/f1Uq96RSr5yUVzMiG8hBM7Njv/CgT4JotloNMGHiHD5PBAiSgO3bs+fRAD5u6HMyGUHChqv803on5M5BmkREC5IB2AZRY/7CxLwDACAiWm8uiBG0CAT33c8kP0EYufTmEhABM0BZ7PsP+ym0OwQgo/cXGbCjgWI21AWNX77/Xk/beeyFke2V8iKCgVUqlAA21l/xb5/ZAYB4INrrWwphMrt71CwwgbrO2v/yLXiP5R4Ys2+vrkaKwUCfI4SV14HIzqX9fb9H5hPCWN9WC7kYZnMfWHAVxUBVbMvr7/+YtyypnRzLlxUNMy1mo9AYo1BFNh2F/vHbf/55SzVPSP+2ztbVObRFJ2GMgSmorsDce17/9v1yowkA7F/e27JhWYiX19a3r2uPzPMjTUeOi3/Eb7zVVgDI9c8LX9qSpbb2bTUmlgz0tzWQLVpa9d/3DWfJNoDty8tYI1IxkWw5L7W2w4jOA+hWekDLny4GCAQQ27sdERnIJZIM960xlm4uy9KigFke35azBALsb2ttaZSKNcooz30vezh60IIsLhPrWY0Brl8HotM1C679yoSOyphVzg5ORsIIrwRANuTrti9HRhcdV2+vy7W7xI61oi0XXRvRdbTZziJraGsJYif7y5HqcdEoTfWt8ZhLuy6UUnBlOwCgMZdCERdiJV+Dmpa3vcZLeNS1RYywTMtnPTZGoIVkEDWjg90LGpYdAz1gUKJYMW5dooENcBBJamb1VmN+pUSbHYHKblNl+vxjgklnJpItJnV4Exr615DRV1+GMEuyz/5xsnhg9ZyrlhZHW2IV32tsCFPseVS6UBFx9ic3V2EseYz3H9U31EdW5b9eWi+4rgeAtI1ovPfBQJGp3dvenNtLG7szljI7IYdmqwLUPKt0FozriLzs46gCDs36GLl7EdMqllxgyfKsqVvG6uOtDrPHLLRqGt+zMEITLJPTZTRgjiqZAJrrY0lP1iyYQIacuNKz0lUiirTsOYZhAA26XLZSuYLFpILVMgZdJZSzQkW5hnRvfZ7XRR6liIg41PoUqzRMccyNFEqQniC+LoFWRwbRGVWhK2ooiKp5BBAsFCTfG6zH/sKQzLAbRSO6LdvFIIwqa1ifPdl17QGiQEjhsPQBl5Myiw5NV/EmTm6AMfeVtICocJTggk3AAtKENH3bitEA2CMzQMGcDAXJgmXYgEi7hHEXprMnR18JyWCEgaCFu7KStoRx38pNXzzZDBi2aIgwbBACCcucdReih1hExtkMeP56tB8HiDUfiLuKWTe99y1eAaZhQACeOJ608pT6J+U1gdsKfkL4Z3kl4ZPq8d63ED6fPFsFiARA/wJ5MiVn0PHpR+725X75K+C2FPOM7wzed0Nzk59nW/G4YOBmdz4NE41PM/RHq9QeyaHxxPH/5j6z3Kc9XIo/j38c/wMffQRepks6RAAAAABJRU5ErkJggg=='), 
'N_INP_NF_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=79510000.0), 
'N_INP_NF_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=253.547), 
'N_INP_NF_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=234.369), 
'N_LEG2_GREEN_NF_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=19.087), 
'N_LEG2_GREEN_NF_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=80390000.0), 
'N_LEG2_GREEN_NF_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='km'), data=289.157), 
'N_LEG2_GREEN_NF_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units='km'), data=197.454), 
'N_UNCOMP_FF_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'N_UNCOMP_FF_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'N_UNCOMP_FF_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'N_UNCOMP_FF_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'N_UNCOMP_NF_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=14.643), 
'N_UNCOMP_NF_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=43880000.0), 
'N_UNCOMP_NF_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=316.275), 
'N_UNCOMP_NF_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=244.702), 
'SAD_DELAY_VALUE': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=0.0), 
'SAD_NF_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'SAD_NF_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'SAD_NF_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'SAD_NF_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'S_UNCOMP_EX_NF_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'S_UNCOMP_EX_NF_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'S_UNCOMP_EX_NF_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'S_UNCOMP_EX_NF_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'S_UNCOMP_FF_E': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'S_UNCOMP_FF_INTEGRATION': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'S_UNCOMP_FF_XPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan), 
'S_UNCOMP_FF_YPOS': ScalarChannelModel(metadata=ScalarChannelMetadataModel(channel_dtype='scalar', units=None), data=nan)}



Manifest e.g:
'_id': '20231109112502', 
'channels': {
'GEM_SHOT_NUM_VALUE': {'name': 'Gemini shot number', 'path': '/CONTROL_SYS/GEM_TA/SHOT_NUM', 'type': 'scalar'}, 
'GEM_SHOT_SOURCE_STRING': {'name': 'Gemini shot source string value', 'path': '/CONTROL_SYS/GEM_TA/SHOT_SOURCE', 'type': 'scalar', 'historical': True}, 
'GEM_SHOT_TYPE_STRING': {'name': 'Gemini shot type', 'path': '/CONTROL_SYS/GEM_TA/SHOT_TYPE', 'type': 'scalar'}, 
'GEM_WP_POS_VALUE': {'name': 'LA3 waveplate setting', 'path': '/CONTROL_SYS/GEM_TA/POS', 'type': 'scalar', 'notation': 'normal', 'units': 'ms'}, 
'N_COMP_CALCULATEDE_VALUE': {'name': 'North compressed calculated value', 'path': '/LA3/N_COMP/ENERGY', 'type': 'scalar', 'units': 'mm'}, 
'N_COMP_FF_E': {'name': 'North compressed far field energy', 'path': '/LA3/N_COMP/IMAGE', 'type': 'scalar', 'notation': 'scientific', 'precision': 4, 'units': 'mg'}, 
'N_COMP_FF_IMAGE': {'name': 'North compressed far field image', 'path': '/LA3/N_COMP/IMAGE', 'type': 'image'}, 
'N_COMP_FF_INTEGRATION': {'name': 'North compressed far field integration value', 'path': '/LA3/N_COMP/IMAGE', 'type': 'scalar', 'notation': 'normal', 'precision': 3, 'units': 'µm'}, 
'N_COMP_FF_XPOS': {'name': 'North compressed far field - x', 'path': '/LA3/N_COMP/IMAGE', 'type': 'scalar', 'notation': 'normal', 'precision': 5, 'units': 'mm'}, 
'N_COMP_FF_YPOS': {'name': 'North compressed far field - y', 'path': '/LA3/N_COMP/IMAGE', 'type': 'scalar', 'notation': 'normal', 'precision': 6, 'units': 'mm'}, 
'N_COMP_THROUGHPUTE_VALUE': {'name': 'North beam compressed throughput value', 'path': '/LA3/N_COMP/ENERGY', 'type': 'scalar', 'units': 'cm'}, 
'TA3_SHOT_NUM_VALUE': {'name': 'Target area 3 shot number', 'path': '/CONTROL_SYS/GEM_TA/SHOT_NUM', 'type': 'scalar', 'historical': True}, 'Type': {'name': 'Data type', 'path': '/Dataset', 'type': 'scalar'}, 
'N_COMP_NF_E': {'name': 'North beam compressed near field energy', 'path': '/LA3/N_COMP/IMAGE', 'type': 'scalar'}, 
'N_COMP_NF_IMAGE': {'name': 'North compressed near field image', 'path': '/LA3/N_COMP/IMAGE', 'type': 'image'}, 
'N_COMP_NF_INTEGRATION': {'name': 'North compressed near field integration value', 'path': '/LA3/N_COMP/IMAGE', 'type': 'scalar', 'notation': 'scientific', 'precision': 4}, 
'N_COMP_NF_XPOS': {'name': 'North compressed near field - x', 'path': '/LA3/N_COMP/IMAGE', 'type': 'scalar', 'units': 'mm'}, 
'N_COMP_NF_YPOS': {'name': 'North compressed near field - y', 'path': '/LA3/N_COMP/IMAGE', 'type': 'scalar', 'units': 'mm'}, 
'N_COMP_SPEC_TRACE': {'name': 'North compressed spec waveform', 'path': '/LA3/N_COMP/SPEC', 'type': 'waveform', 'x_units': 's', 'y_units': 'kJ'}, 
'N_LEG1_GREEN_NF_E': {'name': 'North pump near field energy', 'path': '/LA3/N_PUMP/IMAGE', 'type': 'scalar'}, 
'N_LEG1_GREEN_NF_IMAGE': {'name': 'North pump R-beam image', 'path': '/LA3/N_PUMP/IMAGE', 'type': 'image'}, 
'N_LEG1_GREEN_NF_INTEGRATION': {'name': 'North pump near field integration value', 'path': '/LA3/N_PUMP/IMAGE', 'type': 'scalar', 'historical': True}, 
'N_LEG1_GREEN_NF_XPOS': {'name': 'North pump near field - x', 'path': '/LA3/N_PUMP/IMAGE', 'type': 'scalar', 'notation': 'scientific', 'units': 'µm'}, 
'N_LEG1_GREEN_NF_YPOS': {'name': 'North pump near field - y', 'path': '/LA3/N_PUMP/IMAGE', 'type': 'scalar', 'units': 'µm'}, 
'N_FLUOR_E': {'name': 'North beam fluorescence energy', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar', 'notation': 'normal'}, 
'N_FLUOR_IMAGE': {'name': 'North beam fluorescence image', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'image'}, 
'N_FLUOR_INTEGRATION': {'name': 'North beam fluorescence integration value', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar', 'notation': 'scientific'}, 
'N_FLUOR_XPOS': {'name': 'North beam fluorescence pointing - x', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar'}, 
'N_FLUOR_YPOS': {'name': 'North beam fluorescence pointing - y', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar'}, 
'N_INP_NF_E': {'name': 'North amplifier input near field energy', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar'}, 
'N_INP_NF_IMAGE': {'name': 'North amplifier input near field image', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'image'}, 
'N_INP_NF_INTEGRATION': {'name': 'North amplifier input near field integration value', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar', 'notation': 'scientific'}, 
'N_INP_NF_XPOS': {'name': 'North amplifier input near field - x', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar'}, 
'N_INP_NF_YPOS': {'name': 'North amplifier input near field - y', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar'}, 
'N_LEG2_GREEN_NF_E': {'name': 'North pump R near field energy', 'path': '/LA3/N_PUMP/IMAGE', 'type': 'scalar'}, 
'N_LEG2_GREEN_NF_INTEGRATION': {'name': 'North pump R near field integration value', 'path': '/LA3/N_PUMP/IMAGE', 'type': 'scalar', 'notation': 'scientific', 'precision': 4}, 
'N_LEG2_GREEN_NF_XPOS': {'name': 'North pump R near field - x', 'path': '/LA3/N_PUMP/IMAGE', 'type': 'scalar', 'units': 'km'}, 
'N_LEG2_GREEN_NF_YPOS': {'name': 'North pump R near field - y', 'path': '/LA3/N_PUMP/IMAGE', 'type': 'scalar', 'units': 'km'}, 
'N_UNCOMP_FF_E': {'name': 'North uncompressed far field energy', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar'}, 
'N_UNCOMP_FF_INTEGRATION': {'name': 'North uncompressed far field integration value', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar', 'notation': 'scientific'}, 
'N_UNCOMP_FF_XPOS': {'name': 'North uncompressed far field - x', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar'}, 
'N_UNCOMP_FF_YPOS': {'name': 'North uncompressed far field - y', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar'}, 
'N_UNCOMP_NF_E': {'name': 'North beam amplified energy', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar', 'notation': 'scientific', 'precision': 3}, 
'N_UNCOMP_NF_INTEGRATION': {'name': 'North uncompressed near field integration value', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar', 'notation': 'scientific', 'precision': 2}, 
'N_UNCOMP_NF_XPOS': {'name': 'North uncompressed near field - x', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar'}, 
'N_UNCOMP_NF_YPOS': {'name': 'North uncompressed near field - y', 'path': '/LA3/N_UNCOMP/IMAGE', 'type': 'scalar'}, 
'SAD_DELAY_VALUE': {'name': 'SAD stage position', 'path': '/LA3/SAD_TABLE/DELAY', 'type': 'scalar', 'historical': True}, 
'SAD_NF_E': {'name': 'SAD table near field energy', 'path': '/LA3/SAD_TABLE/IMAGE', 'type': 'scalar'}, 
'SAD_NF_INTEGRATION': {'name': 'SAD table near field integration value', 'path': '/LA3/SAD_TABLE/IMAGE', 'type': 'scalar'}, 
'SAD_NF_XPOS': {'name': 'SAD table near field - x', 'path': '/LA3/SAD_TABLE/IMAGE', 'type': 'scalar'}, 
'SAD_NF_YPOS': {'name': 'SAD table near field - y', 'path': '/LA3/SAD_TABLE/IMAGE', 'type': 'scalar'}, 
'S_UNCOMP_EX_NF_E': {'name': 'South uncompressed expanded beam near field energy', 'path': '/LA3/S_UNCOMP/IMAGE', 'type': 'scalar'}, 
'S_UNCOMP_EX_NF_INTEGRATION': {'name': 'South uncompressed expanded beam near field integration value', 'path': '/LA3/S_UNCOMP/IMAGE', 'type': 'scalar', 'notation': 'normal', 'precision': 5}, 
'S_UNCOMP_EX_NF_XPOS': {'name': 'South uncompressed expanded beam near field - x', 'path': '/LA3/S_UNCOMP/IMAGE', 'type': 'scalar'}, 
'S_UNCOMP_EX_NF_YPOS': {'name': 'South uncompressed expanded beam near field - y', 'path': '/LA3/S_UNCOMP/IMAGE', 'type': 'scalar'}, 
'S_UNCOMP_FF_E': {'name': 'South uncompressed far field energy', 'path': '/LA3/S_UNCOMP/IMAGE', 'type': 'scalar'}, 
'S_UNCOMP_FF_INTEGRATION': {'name': 'South uncompressed far field integration value', 'path': '/LA3/S_UNCOMP/IMAGE', 'type': 'scalar'}, 
'S_UNCOMP_FF_XPOS': {'name': 'South uncompressed far field - x', 'path': '/LA3/S_UNCOMP/IMAGE', 'type': 'scalar'}, 
'S_UNCOMP_FF_YPOS': {'name': 'South uncompressed far field - y', 'path': '/LA3/S_UNCOMP/IMAGE', 'type': 'scalar'}, 
'AMP2_PUMP_E_PELT_VALUE': {'name': 'Amplifier 2 pump energy', 'path': '/LA1_AMP_2/PUMP/ENERGY', 'type': 'scalar', 'units': 'mV'}, 
'GAS_REM_BOTTLE_A_VALUE': {'name': 'Gas bottle A remaining', 'path': '/CONTROL_SYS/GAS_SYSTEM/METROLOGY', 'type': 'scalar', 'units': 'bar', 'historical': True}, 
'GAS_REM_BOTTLE_C_VALUE': {'name': 'Gas bottle C remaining', 'path': '/CONTROL_SYS/GAS_SYSTEM/METROLOGY', 'type': 'scalar', 'units': 'bar'}, 
'LA3_N_COMP_B_PRES_VALUE': {'name': 'LA3 north compressed B present', 'path': '/CONTROL_SYS/GAS_SYSTEM/METROLOGY', 'type': 'scalar', 'units': 'mbara'}, 
'MEZZ_ROOM_T_VALUE': {'name': 'Mezzanine room temperature', 'path': '/CONTROL_SYS/ROOM/METROLOGY', 'type': 'scalar', 'units': 'C'}, 
'REG_3_AT_CHAMBER_VALUE': {'name': 'Regulator 3 pressure at chamber', 'path': '/CONTROL_SYS/ROOM/METROLOGY', 'type': 'scalar', 'units': 'bar'}, 
'SADSTAGE_DELAY_VALUE': {'name': 'SAD stage delay', 'path': '/LA3/SLIDE/POS', 'type': 'scalar', 'units': 'count'}, 
'TA3_ROOM_SUPPLY_BOTTLE_A_VALUE': {'name': 'TA3 supply bottle A value', 'path': '/CONTROL_SYS/ROOM/METROLOGY', 'type': 'scalar', 'notation': 'scientific', 'precision': 2, 'units': 'bar'}, 
'VAC_SYS_CHAMBER_B_PRES_VALUE': {'name': 'Chamber B vacuum system present value', 'path': '/CONTROL_SYS/GEM_TA/PRES', 'type': 'scalar', 'notation': 'scientific', 'precision': 2, 'units': 'mbar'}}
"""
