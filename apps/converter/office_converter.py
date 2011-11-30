import os
import subprocess
import logging

from mimetype.api import get_mimetype
from common.conf.settings import TEMPORARY_DIRECTORY
from common.utils import id_generator

from converter.conf.settings import UNOCONV_PATH, UNOCONV_USE_PIPE
from converter.exceptions import (OfficeConversionError,
    OfficeBackendError, UnknownFileFormat)

CACHED_FILE_SUFFIX = u'_office_converter'
    
CONVERTER_OFFICE_FILE_MIMETYPES = [
    'application/msword',
    'application/mswrite',
    'application/mspowerpoint',
    'application/msexcel',
    'application/vnd.ms-excel',
    'application/vnd.ms-powerpoint',    
    'text/plain',
    'application/vnd.oasis.opendocument.presentation',
    'application/vnd.oasis.opendocument.text',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.oasis.opendocument.graphics',
    'application/vnd.ms-office',
]

logger = logging.getLogger(__name__)


class OfficeConverter(object):
    def __init__(self):
        self.backend_class = OfficeConverterBackendUnoconv
        self.backend = self.backend_class()
        self.exists = False
        self.mimetype = None
        self.encoding = None
    
    def mimetypes(self):
        return CONVERTER_OFFICE_FILE_MIMETYPES

    def convert(self, input_filepath, mimetype=None):
        self.exists = False
        self.mimetype = None
        self.encoding = None
        
        self.input_filepath = input_filepath

        # Make sure file is of a known office format
        if mimetype:
            self.mimetype = mimetype
        else:
            self.mimetype, self.encoding = get_mimetype(open(self.input_filepath), self.input_filepath, mimetype_only=True)

        if self.mimetype in CONVERTER_OFFICE_FILE_MIMETYPES:
            # Cache results of conversion
            self.output_filepath = os.path.join(TEMPORARY_DIRECTORY, u''.join([self.input_filepath, CACHED_FILE_SUFFIX]))
            self.exists = os.path.exists(self.output_filepath)
            if not self.exists:
                try:
                    self.backend.convert(self.input_filepath, self.output_filepath)
                    self.exists = True
                except OfficeBackendError, msg:
                    # convert exception so that at least the mime type icon is displayed
                    raise UnknownFileFormat(msg)
        
    def __unicode__(self):
        return getattr(self, 'output_filepath', None)
        
    def __str__(self):
        return str(self.__unicode__())
    

class OfficeConverterBackendUnoconv(object):
    def __init__(self):
        self.unoconv_path = UNOCONV_PATH if UNOCONV_PATH else u'/usr/bin/unoconv'
        if not os.path.exists(self.unoconv_path):
            raise OfficeBackendError('cannot find unoconv executable')

    def convert(self, input_filepath, output_filepath):
        '''
        Executes the program unoconv using subprocess's Popen
        '''
        self.input_filepath = input_filepath
        self.output_filepath = output_filepath
        
        command = []
        command.append(self.unoconv_path)

        if UNOCONV_USE_PIPE:
            command.append(u'--pipe')
            command.append(u'mayan-%s' % id_generator())

        command.append(u'--format=pdf')
        command.append(u'--output=%s' % self.output_filepath)
        command.append(self.input_filepath)

        try:
            logger.debug('prev environment: %s' % os.environ)
            proc = subprocess.Popen(command, close_fds=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            return_code = proc.wait()
            logger.debug('post environment: %s' % os.environ)

            readline = proc.stderr.readline()
            if return_code != 0:
                raise OfficeBackendError(proc.stderr.readline())
        except OSError, msg:
            raise OfficeBackendError(msg)
        except Exception, msg:
            logger.error('Unhandled exception: %s' % msg)