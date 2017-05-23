#!/usr/bin/python

import re
import subprocess

devs=[]

for line in open('/proc/partitions'):
    line = line.strip()
    if re.search('sd.$', line):
        dev = line.split(' ')[-1]
        devs.append(dev)

devs=sorted(devs)

hdparms={}
for dev in devs:
    print "hdparm", "-I", "/dev/"+dev
    out = subprocess.check_output(["hdparm", "-I", "/dev/"+dev])
    hdparms[dev] = out.split('\n')

smartctls={}
for dev in devs:
    try:
        print "smartctl", "-a", "/dev/"+dev
        out = subprocess.check_output(["smartctl", "-a", "/dev/"+dev])
        smartctls[dev] = out.split('\n')
    except subprocess.CalledProcessError, e:
        print e
        smartctls[dev] = e.output.split('\n')



p = subprocess.Popen(["zpool", "status"], stdout=subprocess.PIPE)
zpool=p.communicate()[0]
zdevs=[]
zstatus={}
for line in zpool.split('\n'):
    line = line.strip()
    if re.search('^ata-', line):
        line = re.sub('\s+', ' ', line)
        zdev = line.split(' ')[0]
        zstatus[zdev]=line.split(' ')[1]
        zdevs.append(zdev)

models={}
serials={}

for dev in hdparms:
    hdparm = hdparms[dev]
    model=""
    serial=""
    for line in hdparm:
        line = line.strip()
        if re.search('Model Number', line):
            model=re.sub('Model Number:\s+', '', line).replace(' ', '_')
        if re.search('Serial Number', line):
            serial=re.sub('Serial Number:\s+', '', line).replace(' ', '_')

    models[dev]=model
    serials[dev]=serial

statuses = {
    'OK': '\033[92m     OK\033[0m',
    'WARNING': '\033[93mWARNING\033[0m',
    'PREFAIL': '\033[91mPREFAIL\033[0m',
    'FAILURE': '\033[41mFAILURE\033[0m'
}

print " %3s|%12s|%7s|%7s|%7s|%7s|%8s|%7s| %s " %( "dev", "zstatus", "relloc", "pending", "uncorr", "diskerr", "hours_on", "STATUS", "ata")
for dev in devs:
    ata="ata-"+models[dev]+"_"+serials[dev]
    rellocated=0
    uncorrectable=0
    pending=0
    diskerr=0
    diskstatus=''
    hours=0

    for line in smartctls[dev]:
        line = line.strip()
        line=re.sub('\s+', ' ', line);
        c=0
        remap=0
        if re.search('Reallocated_Sector_Ct', line):
            rellocated=line.split(' ')[-1]
            rellocated=int(rellocated)
        if re.search('Current_Pending_Sector', line):
            pending=line.split(' ')[-1]
            pending=int(pending)
        if re.search('Offline_Uncorrectable', line):
            uncorrectable=line.split(' ')[-1]
            uncorrectable=int(uncorrectable)
        if re.search('ATA Error Count:', line):
            diskerr=line.split(' ')[3]
            diskerr=int(diskerr)
        if re.search('Power_On_Hours', line):
            hours=line.split(' ')[-1]
            hours=int(hours)
        for v in [rellocated, pending, uncorrectable, diskerr]:
            if bool(v):
                c += 1
                remap += v
    if c == 0 and remap == 0:
        diskstatus=statuses['OK']
    if c == 1 and remap in range(1, 100) or hours > 42424:
        diskstatus=statuses['WARNING']
    if c == 2 or remap in range(100, 150):
        diskstatus=statuses['PREFAIL']
    if c > 2 or remap >= 150:
        diskstatus=statuses['FAILURE']


    if ata in zdevs:
        print " %3s|%12s|%7s|%7s|%7s|%7s|%8s|%7s| %s" %( dev, zstatus[ata], rellocated, pending, uncorrectable, diskerr, hours, diskstatus, ata)
    else:
        print " %3s|%12s|%7s|%7s|%7s|%7s|%8s|%7s| %s" %( dev, "NOT_IN_ZPOOL", rellocated, pending, uncorrectable, diskerr, hours, diskstatus, ata)

print "\n\nHDDs test tool. For more information read https://www.backblaze.com/blog/what-smart-stats-indicate-hard-drive-failures/"
