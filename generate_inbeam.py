#!/usr/local/bin/python
import sys
import os
import shutil
import logging
import configparser
import argparse
import time
import subprocess


def get_args():
    '''This function parses and returns arguments passed in'''
    # Assign description to the help doc
    description = 'Self-calibrate a single-source dataset'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-msfile', dest='msfile', help='path to single-source MS')
    parser.add_argument('-config', dest='config_file',
                        help='Configuration file. Defatult ./config.cfg', default='./config.cfg')

#    parser.add_argument('--restore_flags', action='store_true',
#                        help='Restore the first available flag version. Default is False', default=False)
#    # Manually generate a mask
#    parser.add_argument('--make_mask', dest='make_mask', action='store_true',
#                        help='Make manual mask', default=False)
#    parser.add_argument('--mask_spw', dest='mask_spw', default='3',
#                        help='spw selection for masking')
#    parser.add_argument('--mask_cell', dest='mask_cell', default='',
#                        help='cell size selection for masking')
#    # Select specific loops to run
#    parser.add_argument('-r', '--run_loop', dest='loops', type=str, nargs='+',
#                        help='whitespace separated list of loops to run',
#                        default='')
    parser.add_argument('--debug', dest='do_debug', action='store_true',
                       help='run in debug mode', default=False)
    args = parser.parse_args()
    return args

def get_logger(
        LOG_FORMAT      = '%(asctime)s | %(levelname)s | %(message)s',
        LOG_FORMAT_CODE = '#%(asctime)s\n%(message)s\n',
        DATE_FORMAT     = '%Y-%m-%d %H:%M:%S',
        LOG_NAME        = 'logger',
        LOG_FILE_INFO   = 'mylog.log',
        LOG_FILE_CODE   = 'executed_code.log.py',
        do_debug        = False):

    # Add new level to keep code
    code_level = 55
    logging.addLevelName(code_level, 'CODE')

    def code(self, message, *args, **kws):
        self.log(code_level, message, *args, **kws)
    logging.Logger.code = code

    #Set message level
    msg_level = logging.INFO
    if do_debug: msg_level = logging.DEBUG

    logger = logging.getLogger(LOG_NAME)
    log_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    log_formatter_code = logging.Formatter(fmt=LOG_FORMAT_CODE, datefmt=DATE_FORMAT)
    logging.Formatter.converter = time.gmtime

    # comment this to suppress console output    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)

    # File mylog.log with all information
    file_handler_info = logging.FileHandler(LOG_FILE_INFO, mode='w')
    file_handler_info.setFormatter(log_formatter)
    file_handler_info.setLevel(msg_level)
    logger.addHandler(file_handler_info)

    # File to keep executed code
    file_handler_code = logging.FileHandler(LOG_FILE_CODE, mode='w')
    file_handler_code.setFormatter(log_formatter_code)
    file_handler_code.setLevel(code_level)
    logger.addHandler(file_handler_code)

    logger.setLevel(msg_level)
    return logger

def makedir(pathdir):
    try:
        os.mkdir(pathdir)
        logger.info('Create directory: {}'.format(pathdir))
        logger.code('os.mkdir("{}")'.format(pathdir))
    except:
        logger.debug('Cannot create directory: {}'.format(pathdir))
        pass

def copydir(pathdir, destination):
    try:
        shutil.copytree(pathdir, destination)
        logger.info(f'Copy directory: {pathdir} to {destination}')
        logger.code(f'shutil.copytree("{pathdir},{destination}")')
    except:
        logger.debug(f'Copy directory: {pathdir} to {destination}')
        pass

def drop_key(dictionary, key):
    try:
        dictionary.pop(key)
    except KeyError:
        pass
    return dictionary

def rmfile(pathdir,message='Deleted:'):
    if os.path.exists(pathdir):
        try:
            os.remove(pathdir)
            logger.info('{0} {1}'.format(message, pathdir))
            logger.code('os.remove("{}")'.format(pathdir))
        except:
            logger.debug('Could not delete: {0} {1}'.format(message, pathdir))
            pass

def rmdir(pathdir, message='Deleted:'):
    if os.path.exists(pathdir):
        try:
            shutil.rmtree(pathdir)
            logger.info('{0} {1}'.format(message, pathdir))
            logger.code('shutil.rmtree("{}")'.format(pathdir))
        except:
            logger.info('Could not delete: {1}'.format(message, pathdir))
            pass

def read_config(config_file):
    ''' Read configuration file. '''
    config = configparser.ConfigParser()
    logger.info(f'Reading config file: {config_file}')
    config.read(config_file)
    logger.debug(f'Sections: {config.sections()}')
    return config

def run_casa_command(config_command, key):
    command_name = key
    logger.debug(f'Dictionary passed to {command_name}')
    logger.debug(config_command[command_name])
    logger.info(f'Running command: {command_name}')
    lines = []
    for (k,v) in config_command[command_name].items():
        #logger.debug(f'{k}: {v}')
        t = type(v)
        if t == str:
            lines.append('{0}="{1}"'.format(k,v))
        elif t == int or t == float:
            lines.append('{0}={1}'.format(k,v))
        elif t == list:
            lines.append('{0}={1}'.format(k,v))
        elif t == bool:
            lines.append('{0}={1}'.format(k,v))
        elif t == dict:
            lines.append('{0}={1}'.format(k,v))
        else:
            logger.warning('Could not identify type '
                           'of paremeter {0}, {1}'.format(k,v))
    output = '{0}({1})'.format(command_name, ', '.join(lines))
    logger.code(output)
    subprocess.call([casa_command, '--nogui', '--nologger','--nologfile', '-c', output]) 

def split_all_directions(msfile, positions):
    logger.info('Starting split_all_directions')
    config_split = config['split_all']
    run_name = os.path.splitext((os.path.basename(msfile)))[0]
#    msfile_name = os.path.basename(msfile)[0]
    out_msfiles = []
    outdir = f"{config['global']['split_individual_dir']}"
    makedir(outdir)
    for i, position in enumerate(positions):
        outputvis = f"{outdir}/{run_name}_{i:03d}.ms"
        out_msfiles.append(outputvis)
        if not os.path.exists(outputvis):
            split_individual(vis=msfile, outputvis=outputvis, position=position,
                             cavg=config_split['cavg'], tavg=config_split['tavg'])
        else:
            logger.info(f'Already exists: {outputvis}')
    return out_msfiles

def split_individual(vis, outputvis, field='',
                    timeaverage=True, tavg='8s',
                    chanaverage=True, cavg=8,
                    datacolumn='data',
                    position=''):
    inter_ms = f"{outputvis}.tmp"
    listobs_file = f'{outputvis}.listobs.txt'
    # Clean files
    rmdir(outputvis)
    rmdir(inter_ms)
    rmfile(listobs_file)
    #
    copydir(vis, inter_ms) 
    # Define commands
    commands = {}
    commands['fixvis'] = {
        'vis': inter_ms,
        'field': field,
        'outputvis': '',
        'phasecenter': position,
        'datacolumn': datacolumn}
    commands['mstransform'] = {
        'vis' : inter_ms,
        'outputvis' : outputvis,
        'field': field,
        'datacolumn': datacolumn,
        'keepflags' : True,
        'timeaverage':timeaverage,'timebin':tavg,
        'chanaverage':chanaverage,'chanbin':int(cavg)}
    commands['listobs'] = {
        'vis': vis,
        'listfile': listobs_file}
    # Run commands
    run_casa_command(commands, 'fixvis')
    run_casa_command(commands, 'mstransform')
    if os.path.isdir(outputvis):
        rmdir(inter_ms)
    else:
        logger.critical(f'There was a problem creating {outputvis}')
        sys.exit(1)
    run_casa_command(commands, 'listobs')

def run_wsclean_all(msfiles, section):
    logger.info('Starting run_wsclean_all')
    img_path = config[section]['img_path']
    makedir(img_path)
    new_images = []
    for i, msfile in enumerate(msfiles):
        basename = os.path.basename(msfile)
        img_dir = f'{img_path}/{basename[:-3]}' 
        if os.path.exists(img_dir):
            logger.info(f'Already exists: {img_dir}')
        else:
            makedir(img_dir)
            config_wsclean = dict(config[section]).copy()
            logger.info(f'Now processing {msfile}')
            img_name = f'{img_dir}/{basename[:-3]}'
            wsclean_command = write_wsclean_command(config_wsclean, msfile, img_name)
            logger.code('os.system("{}")'.format(wsclean_command))
            os.system(wsclean_command)
            new_images.append(i)
    return new_images


#def find_cellsize(msfile):
#    band = check_band(msfile)
#    if band == 'L':
#        cellsize = 0.03
#    elif band == 'C':
#        cellsize = 0.008
#    elif band == 'K':
#        cellsize = 0.002
#    return cellsize

def write_wsclean_command(config_wsclean, msfile, img_name):
    config_wsclean['-name'] = img_name
    logger.debug('config_wsclean')
    logger.debug(config_wsclean)
#    msfile = config_wsclean['vis'] # vis is not a parameter and will be removed
#    # Set up cellsize:
#    cellsize = config_wsclean.get('-scale', find_cellsize(msfile))
#    # Fix scale (cellsize) if not string
#    if type(cellsize) != str:
#        cellsize = '{0}asec'.format(cellsize)
#    config_wsclean['-scale'] = cellsize
#    # Duplicate size if needed:
    if len(config_wsclean['-size'].split(' '))==1:
        size_int = config_wsclean['-size']
        config_wsclean['-size'] = '{0} {0}'.format(size_int)
#    # Set up robust
    if config_wsclean['-weight'] == 'briggs' and '-robust' in config_wsclean.keys():
        robust = config_wsclean['-robust']
        config_wsclean['-weight'] = 'briggs {0}'.format(robust)
        config_wsclean.pop('-robust')
    # Skip casa-mask if no mask specified
    if config_wsclean['-casa-mask'] == '':
        config_wsclean.pop('-casa-mask')

    # Only keep keys starting with - that will be passed to wsclean
    for key in list(config_wsclean.keys()):
        if key[0] != '-':
            config_wsclean = drop_key(config_wsclean, key)
    wsclean_params = ' '.join(['{0} {1}'.format(k,v)
                                for (k,v) in config_wsclean.items()])
    wsclean_command = '{0} {1} {2}'.format('wsclean',
                                           wsclean_params,
                                           msfile)
    return wsclean_command

def read_outliers_file(infile):
    logger.info(f'Reading outliers file: {infile}')
    positions = []
    logger.info('Positions:')
    with open(infile, 'r') as f:
        lines = f.readlines()
        for line in lines:
      	    if line[0] != '#' and 'phasecenter' in line:
                position = line.split('=')[-1].strip()
                positions.append(position)
                logger.info(position)
    return positions

def first_images(msfiles):
    new_images = run_wsclean_all(msfiles, section='wsclean')
    logger.info('Starting divide_by_model')
    for i, msfile in enumerate(msfiles):
        if i in new_images:
            divide_by_model(msfile)
            adjust_phase_centre(msfile, [0,0])
        else:
            logger.info(f'No divide_model needed for existing image for {msfile}')
    run_wsclean_all(msfiles, section='wsclean_unit')

def adjust_phase_centre(msfile, position=[0,0]):
    logger.info(f'Recentering {msfile}')
    adjust_phase_center = os.path.split(sys.argv[0])[0]+'/adjust_phase_center.py'
    logger.debug(f'Running script: {adjust_phase_center}')
    do_logfile = '--nologfile'
    position_str = ','.join([str(p) for p in position])
    subprocess.call([casa_command, '--nogui', '--nologger', do_logfile, '-c', f'{adjust_phase_center}', '-msfile',f'{msfile}', '-position', position_str])
    return

def divide_by_model(msfile):
    logger.info(f'Dividing model for {msfile}')
    divide_model_path = os.path.split(sys.argv[0])[0]+'/divide_model.py'
    logger.debug(f'Running script: {divide_model_path}')
    do_logfile = '--nologfile'
    subprocess.call([casa_command, '--nogui', '--nologger', do_logfile, '-c', f'{divide_model_path}', '-msfile',f'{msfile}'])
    return

def concatenate_all(msfile, msfiles):
    logger.info(f"Running concatenate")
    run_name = os.path.splitext((os.path.basename(msfile)))[0]
    outdir = f"{config['global']['split_dir']}"
    concatvis = f"{outdir}/{run_name}_concat.ms"
    # Define commands
    commands = {}
    commands['concat'] = {
        'vis': msfiles,
        'concatvis': concatvis,
        'respectname': False}
    commands['listobs'] = {
        'vis': concatvis,
        'listfile': f"{concatvis}.listobs.txt"}
    # Run commands
    if os.path.exists(concatvis):
        logger.info(f'Already exists: {concatvis}')
    else:
        run_casa_command(commands, 'concat')
        run_casa_command(commands, 'listobs')
    return concatvis


def image_concatenate(msfile, section='wsclean_unit'):
    config_wsclean = dict(config[section]).copy()
    img_path = config[section]['img_path']
    basename = os.path.basename(msfile)
    img_dir = f'{img_path}/{basename[:-3]}' 
    img_name = f'{img_dir}/{basename[:-3]}'
    if os.path.exists(img_dir):
        logger.info(f'Already exists: {img_dir}')
    else:
        makedir(img_dir)
        config_wsclean = dict(config[section]).copy()
        logger.info(f'Now processing {msfile}')
        img_name = f'{img_dir}/{basename[:-3]}'
        wsclean_command = write_wsclean_command(config_wsclean, msfile, img_name)
        logger.code('os.system("{}")'.format(wsclean_command))
        os.system(wsclean_command)



def main():
    positions = read_outliers_file(config['sources']['outliers_file'])
    msfile = args.msfile
    msfiles = split_all_directions(msfile, positions)
    first_images(msfiles)
    concatvis = concatenate_all(msfile, msfiles)
    image_concatenate(concatvis)

if __name__ == '__main__':
    args = get_args()
    logger = get_logger(do_debug=args.do_debug) # Set up your logger
    config = read_config(args.config_file)
    casa_command = config['global']['casa']
    main()

