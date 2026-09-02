function pp2any(infilename, elmname, segname)
%PP2ANY Convert pp files to reference nodes for use in AnyScript.
%   PP2ANY(INFILE,ELM,SEG) parses the file named INFILE and creates
%   the file with the name ELM_SEG_nodes.any for direct inclusion in
%   the anyscript code.
%
%   INFILE is the origin file name, e.g. MPFL.pp from MeshLab
%   ELM is the name of the element, e.g. ligament name 'MPFL'
%   SEG is the name of the segment, e.g. 'patella'

try
    disp(['Parsing ',infilename,'...']);
catch
    error('Input file name MUST be given!');
end
if not(exist('elmname','var'))
    elmname = '';
end
[xmldata] = parse(infilename);
if not(exist('segname','var'))
    outfilename = [infilename(1:end-2),'any'];
else
    outfilename = [elmname,segname,'_nodes.any'];
end
ofp = fopen(outfilename, 'w');
ii = 0;
while true
    ii = ii + 1;
    try
        fprintf(ofp...
            ,['AnyRefNode ',elmname,'Node = {\n'...
            ,'  AnyVec3 sRel_us = {%s,%s,%s}*0.001;\n'...
            ,'  DEF_REFNODE_CUSTOM_SCALING_1arg(sRel_us)\n'...
            ,'};\n']...
            ,xmldata(2).Children(2*(1+ii)).Attributes(3).Value...
            ,xmldata(2).Children(2*(1+ii)).Attributes(4).Value...
            ,xmldata(2).Children(2*(1+ii)).Attributes(5).Value...
            ...
            );
    catch
        fclose('all');
        break
    end
end
disp([outfilename,' successfully created.']);
end

function [theStruct] = parse(filename)
% PARSEXML Convert XML file to a MATLAB structure.
try
    tree = xmlread(filename);
catch
    error('%s not found.',filename);
end

% Recurse over child nodes. This could run into problems
% with very deeply nested trees.
try
    [theStruct] = parseChildNodes(tree);
catch
    error('Unable to parse XML file %s.',filename);
end
end


% ----- Subfunction PARSECHILDNODES -----
function [children] = parseChildNodes(theNode)
% Recurse over node children.
children = [];
if theNode.hasChildNodes
    childNodes = theNode.getChildNodes;
    numChildNodes = childNodes.getLength;
    allocCell = cell(1, numChildNodes);
    
    children = struct(             ...
        'Name', allocCell, 'Attributes', allocCell,    ...
        'Data', allocCell, 'Children', allocCell);
    
    for count = 1:numChildNodes
        theChild = childNodes.item(count-1);
        children(count) = makeStructFromNode(theChild);
    end
end
end

% ----- Subfunction MAKESTRUCTFROMNODE -----
function nodeStruct = makeStructFromNode(theNode)
% Create structure of node info.

nodeStruct = struct(                        ...
    'Name', char(theNode.getNodeName),       ...
    'Attributes', parseAttributes(theNode),  ...
    'Data', '',                              ...
    'Children', parseChildNodes(theNode));

if any(strcmp(methods(theNode), 'getData'))
    nodeStruct.Data = char(theNode.getData);
else
    nodeStruct.Data = '';
end
end

% ----- Subfunction PARSEATTRIBUTES -----
function attributes = parseAttributes(theNode)
% Create attributes structure.

attributes = [];
if theNode.hasAttributes
    theAttributes = theNode.getAttributes;
    numAttributes = theAttributes.getLength;
    allocCell = cell(1, numAttributes);
    attributes = struct('Name', allocCell, 'Value', ...
        allocCell);
    
    for count = 1:numAttributes
        attrib = theAttributes.item(count-1);
        attributes(count).Name = char(attrib.getName);
        attributes(count).Value = char(attrib.getValue);
    end
end
end