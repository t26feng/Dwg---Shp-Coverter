;; *************************************************************************************
;;  Created by: Tianyu Feng
;;  Spring 2017
;;  DWG to Shapefile:
;;      The following program consumes a .dwg file or a shapefile along with 
;;      accompanying inputs and creates an updated shapefile in a temp folder to append
;;      to the template specified as fpath
;; *************************************************************************************


#   Import system modules

#import arcpy, os
#from arcpy import env

import arcpy, os, shutil
from Tkinter import *
from tkFileDialog import askopenfilename
from os.path import isdir, join, isfile
import arcpy.conversion # required for CADToGeodatabase_conversion

projections = ['NAD 1983 MTM 9','NAD 1983 MTM 10','NAD 1983 MTM 11','NAD 1983 MTM 12',
               'NAD 1983 MTM 13','NAD 1983 MTM 14', 'NAD 1983 CSRS MTM 9','NAD 1983 CSRS MTM 10',
               'NAD 1983 CSRS MTM 11','NAD 1983 CSRS MTM 12','NAD 1983 CSRS MTM 13',
               'NAD 1983 CSRS MTM 14', 'NAD 1983 UTM Zone 15N','NAD 1983 UTM Zone 16N',
               'NAD 1983 UTM Zone 17N','NAD 1983 UTM Zone 18N','NAD_27_MTM_10',
               'North American Datum 1927', 'North American Datum 1983']

options = ['False', 'True']
    
# Creating the GUI
master = Tk()
master.wm_title("Convert DWG to SHP")

Label(master, text="DWG -> SHP:", 
      fg = 'red', anchor='center', height='2').grid\
    (row=0, column=0, columnspan=6, sticky=W, padx=15)

Label(master, text="Choose dwg or shp file(with extension)").grid(row=1, sticky=W, padx=10, pady=5)
Label(master, text="Enter township name").grid(row=2, sticky=W, padx=10, pady=20)   
Label(master, text="Choose source projection").grid(row=3, sticky=W, padx=10, pady=10)
Label(master, text="Published?").grid(row=4, sticky=W, padx=10, pady=10)

dwgfile = Entry(master, width=40)
shpname = Entry(master, width=40)

variable = StringVar(master)
variable.set(projections[1]) # default value

variable2 = StringVar(master)
variable2.set(options[0]) # default value


Sref = apply(OptionMenu, (master, variable) + tuple(projections))
Published = apply(OptionMenu, (master, variable2) + tuple(options))


dwgfile.grid(row=1, column=1, padx=40)
shpname.grid(row=2, column=1, padx=40)
Sref.grid(row=3, column=1, padx=40)
Published.grid(row=4, column=1, padx=40)

# Arrays
temp = r'C:\temp\shp_create_temp'
fpath = 'Target_Final_Shapefile_Location' #folder location of shapefile, empty shapefile recommended



# Creating the gdb to store converted dwg post feature conversion
# watch for lock files, which lead to ambiguous error messages when trying to run some arcpy methods 

def browse():
    dwgfile.delete('0', END)
    dwgfilename = askopenfilename()
    dwgfile.insert(END, dwgfilename)
    basename = os.path.basename(dwgfilename)
    name = os.path.splitext(basename)[0]
    shpname.delete('0', END)
    shpname.insert(END, name)

def convert():
    
    dwg_path = dwgfile.get()
    shp_name = shpname.get()
    gdbname = shp_name + '.gdb' 
    gdbpath = os.path.join(temp, gdbname)

    print 'creating temp working folder'
    if not os.path.exists(temp):
        os.makedirs(temp)
    else:
        shutil.rmtree(temp)
        os.makedirs(temp)
        
    if os.path.splitext(dwg_path)[1] == '.dwg':
        print 'creating new gdb'
        arcpy.CreateFileGDB_management(temp, gdbname)

        arcpy.env.workspace = gdbpath + '\\' + 'Template'
        arcpy.env.qualifiedFieldNames = False
        arcpy.env.overwriteOutput = True

        #   Execute CreateFeaturedataset
        print 'creating featuredataset from dwg'
        proj = variable.get()

        arcpy.CADToGeodatabase_conversion(dwg_path, gdbpath, 'Template', '1000', spatial_reference = proj) 
        print 'Feature dataset created from CAD drawing'
        
        in_features = arcpy.env.workspace + '\\' + 'Polygon'

        #FeatureClassToFeatureClass_conversion (in_features, out_path, out_name, {where_clause}, {field_mapping}, {config_keyword})
        arcpy.FeatureClassToFeatureClass_conversion(in_features, temp, shp_name + 'unproj' + ".shp")     
        print 'shapefile created'
        ##  Execute DeleteField
        inFeatureName = temp + "\\" + shp_name + 'unproj' + ".shp"

        # cleanup small objects See createSelectionSet.txt 

        dropFieldsShp = ["Entity", "Handle", "LyrFrzn", "LyrLock", "LyrOn", "LyrVPFrzn", "LyrHandle", "Color", "EntColor", "LyrColor", "BlkColor", \
                       "Linetype", "EntLinetyp", "LyrLnType", "BlkLinetyp", "Elevation", "Thickness", "LineWt", "EntLineWt", "LyrLineWt", "BlkLineWt", \
                       "RefName", "LTScale", "ExtX", "ExtY", "ExtZ", "DocName", "DocPath", "DocType", "DocVer", "Shape_Leng", "Shape_Area", "SYMDESC", \
                         "NORTH", "EAST", "IDENT", "ID", "SYMDESC2", "SYMDESC3"]

        arcpy.DeleteField_management(inFeatureName,dropFieldsShp)           # specify fields to drop from the shapefile

        # Create new fields: file_name, proj, and source_prj
        
        # First checks if fields to be added already exist and deletes it if it does
        shp = inFeatureName
        
        fields = ['file_name', 'proj', 'source_prj', 'published']
        
        if os.path.isfile(shp):
            for fn in fields:
                arcpy.DeleteField_management(shp, fn)
                
        # Adds new fields to shpfile
        arcpy.AddField_management (shp, 'file_name', 'TEXT', field_length = 30)
        arcpy.AddField_management (shp, 'proj', 'TEXT', field_length = 30)
        arcpy.AddField_management (shp, 'source_prj', 'TEXT', field_length = 30)
        arcpy.AddField_management (shp, 'published', 'TEXT', field_length = 30)
        print 'fields added'

        # Create cursor object for fname and proj fields
        fname_proj_cursor = arcpy.da.UpdateCursor(shp, ['file_name', 'proj'])
        
        # Populate fname and proj fields
        file_name = shp_name
        desc = arcpy.Describe(shp)
        sref = desc.spatialReference
        for row in fname_proj_cursor:
            fname_proj_cursor.updateRow([file_name, sref.name])
            del row
        del fname_proj_cursor
        
        # Create cursor object for source_prj field
        sref_cursor = arcpy.da.UpdateCursor(shp, 'source_prj')
        
        # Populate source_prj field
        if 'CSRS' in sref.name:
            for row in sref_cursor:
                row[0] = 'CSRS'
                sref_cursor.updateRow(row)
                del row
        else:
            for row in sref_cursor:
                row[0] = 'ORIGINAL'
                sref_cursor.updateRow(row)
                del row
        del sref_cursor

        # Create cursor object for published field
        pub_cursor = arcpy.da.UpdateCursor(shp, 'published')
        
        # Populate published field
        pub_status = variable2.get()
        print 'pub_status is ' + pub_status
        for row in pub_cursor:
            row[0] = pub_status
            pub_cursor.updateRow(row)
            del row
        del pub_cursor
         

        # delete unwanted polygons
        
        print 'filtering out unwanted polygons'
        
        keep_list = ['A', 'D', 'L', 'P', 'N']
        
        with arcpy.da.UpdateCursor(shp, 'layer') as cursor: 
            for row in cursor:
                if row[0][0] not in keep_list:
                    cursor.deleteRow()
                    
        print 'fields updated'
        
        # run ORIG_to_CSRS custom projection transformation
        # Comment this out if not working with CSRS shapefiles!! Requires proper gridshitft file (NTV2) and transformation setup to work

        arcpy.env.workspace = temp
        arcpy.env.qualifiedFieldNames = False
        arcpy.env.overwriteOutput = True

        print 'performing gridshift'
        inp = shp
        outp = shp[:-10] + '.shp'
        print inp
        print outp
        out_coor = arcpy.SpatialReference('NAD 1983 CSRS Ontario MNR Lambert')
        print out_coor
        tsfm = 'ORIG_to_CSRS'
        print tsfm
        if 'CSRS' not in sref.name:
            arcpy.Project_management(inp, outp, out_coor, tsfm)
        else:
            outp = shp

                    
            
    
        print 'appending new shpfile to template'
        
        arcpy.env.workspace = fpath
        arcpy.env.qualifiedFieldNames = False
        arcpy.env.overwriteOutput = True
        
        arcpy.Append_management(outp, fpath, 'NO_TEST')
                                
        print 'DONE'
        
    else:
        proj = variable.get()
        arcpy.env.workspace = temp
        arcpy.env.qualifiedFieldNames = False
        arcpy.env.overwriteOutput = True
        

        # Create new fields: file_name, proj, source_prj, and published
        
        # First checks if fields to be added already exist and deletes it if it does
        shp = dwgfile.get()
        
        fields = ['file_name', 'proj', 'source_prj', 'published']
        if os.path.isfile(shp):
            for fn in fields:
                arcpy.DeleteField_management(shp, fn)
                
        # Adds new fields to shpfile
        arcpy.AddField_management (shp, 'file_name', 'TEXT', field_length = 30)
        arcpy.AddField_management (shp, 'proj', 'TEXT', field_length = 30)
        arcpy.AddField_management (shp, 'source_prj', 'TEXT', field_length = 30)
        arcpy.AddField_management (shp, 'published', 'TEXT', field_length = 30)
        print 'fields added'

        # Create cursor object for fname and proj fields
        fname_proj_cursor = arcpy.da.UpdateCursor(shp, ['file_name', 'proj'])
        
        # Populate fname and proj fields
        file_name = shpname.get()
        desc = arcpy.Describe(shp)
        sref = desc.spatialReference
        for row in fname_proj_cursor:
            fname_proj_cursor.updateRow([file_name, sref.name])
            del row
        del fname_proj_cursor
        
        # Create cursor object for source_prj field
        sref_cursor = arcpy.da.UpdateCursor(shp, 'source_prj')
        
        # Populate source_prj field
        if 'CSRS' in sref.name:
            for row in sref_cursor:
                row[0] = 'CSRS'
                sref_cursor.updateRow(row)
                del row
        else:
            for row in sref_cursor:
                row[0] = 'ORIGINAL'
                sref_cursor.updateRow(row)
                del row
        del sref_cursor

        # Create cursor object for published field
        pub_cursor = arcpy.da.UpdateCursor(shp, 'published')
        
        # Populate published field
        pub_status = variable2.get()
        for row in pub_cursor:
            row[0] = pub_status
            pub_cursor.updateRow(row)
            del row
        del pub_cursor


        # delete unwated polygons
        
        print 'filtering out unwated polygons'
        
        keep_list = ['A', 'D', 'L', 'P', 'N']
        
        with arcpy.da.UpdateCursor(shp, 'layer') as cursor:
            for row in cursor:
                if row[0][0] not in keep_list:
                    cursor.deleteRow()
                    
        print 'fields updated' 

        print 'performing gridshift'
        inp = shp
        outname = os.path.basename(shp)[:-4] + '_proj.shp'
        outp = os.path.join(temp, outname)
        print inp
        print outp
        out_coor = arcpy.SpatialReference('NAD 1983 CSRS Ontario MNR Lambert')
        print out_coor
        tsfm = 'ORIG_to_CSRS'
        print tsfm
        if 'CSRS' not in sref.name:
            arcpy.Project_management(inp, outp, out_coor, tsfm)
        else:
            outp = shp
            

        print 'appending new shpfile to template'

        
        arcpy.env.workspace = fpath
        arcpy.env.qualifiedFieldNames = False
        arcpy.env.overwriteOutput = True
        
        arcpy.Append_management(outp, fpath, 'NO_TEST')

        
        print 'DONE'


b = Button(master, text = 'Create Shapefile', command = convert)
b.grid(row=5, column=1, pady=20)

b2 = Button(master, text = 'Browse', command = browse)
b2.grid(row=1, column=2, sticky=W)
mainloop()

