import xml.etree.ElementTree as ET

def GetPointCoordsByName(context, FileName, PointName):
    tree = ET.parse(FileName)
    root = tree.getroot()
    
    list_names = []
    dict_points = {}
    for point in root.findall('point'):
        name = point.get('name')
        x = float(point.get('x'))
        y = float(point.get('y'))
        z = float(point.get('z'))
        list_names.append(name)
        dict_points[name] = (x, y, z)
        
    if PointName in list_names:
        return dict_points[PointName]
    else:
        return (0, 0, 0)
    