"""Bounded original DOCX block/table/image evidence; no inferred caption ownership."""
import hashlib
import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def safe_xml(raw, allow_external_doctype=False):
    if b'<!ENTITY' in raw.upper() or (b'<!DOCTYPE' in raw.upper() and not allow_external_doctype):raise ValueError('XML entities unsupported')
    # ElementTree does not fetch external DTDs; entity declarations remain forbidden.
    return ET.fromstring(raw)


def paragraph(node):
    return ''.join((x.text or '') if x.tag==W+'t' else '\t' if x.tag==W+'tab' else '\n' if x.tag in {W+'br',W+'cr'} else '' for x in node.iter())


def member_name(target):
    if not target or '\\' in target or ':' in target or target.startswith('/') or '..' in target.split('/'):
        raise ValueError('Unsafe DOCX relationship target')
    member=posixpath.normpath('word/'+target)
    if not member.startswith('word/'):raise ValueError('Relationship escapes document')
    return member


def extract(path, asset_directory=None):
    raw=Path(path).read_bytes()
    if len(raw)>20_000_000:raise ValueError('DOCX byte budget exceeded')
    with zipfile.ZipFile(path) as z:
        infos=z.infolist();names=[x.filename for x in infos]
        if len(infos)>2000 or sum(x.file_size for x in infos)>20_000_000:raise ValueError('DOCX uncompressed budget exceeded')
        if len(names)!=len(set(names)):raise ValueError('Ambiguous duplicate archive member')
        root=safe_xml(z.read('word/document.xml'))
        rels={}
        if 'word/_rels/document.xml.rels' in names:
            for x in safe_xml(z.read('word/_rels/document.xml.rels')):
                rid=x.attrib['Id']
                if rid in rels:raise ValueError('Duplicate relationship identity')
                rels[rid]=x.attrib
        blocks=[]
        for i,node in enumerate(root.find(W+'body')):
            text='\n'.join(paragraph(p) for p in node.iter(W+'p'));images=[]
            block={'locator':f'word/document.xml body block {i+1}','kind':node.tag.split('}')[-1],'text':text,'images':images}
            if node.tag==W+'tbl':
                block['table_rows']=[['\n'.join(paragraph(p) for p in cell.iter(W+'p')) for cell in row.findall(W+'tc')] for row in node.findall(W+'tr')]
            for blip in node.iter(A+'blip'):
                rid=blip.attrib.get(R+'embed') or blip.attrib.get(R+'link');rel=rels.get(rid)
                if not rel:raise ValueError('Image relationship missing')
                if rel.get('TargetMode')=='External':
                    images.append({'relationship_id':rid,'external':True,'target':rel.get('Target'),'status':'not_fetched'});continue
                member=member_name(rel.get('Target'));body=z.read(member);h=hashlib.sha256(body).hexdigest()
                image={'relationship_id':rid,'member':member,'sha256':h,'status':'pixels_preserved_not_transcribed'}
                if asset_directory:
                    directory=Path(asset_directory);directory.mkdir(parents=True,exist_ok=True)
                    suffix=Path(member).suffix.lower();suffix=suffix if suffix in {'.png','.jpg','.jpeg','.gif','.tif','.tiff','.bmp','.webp'} else '.bin'
                    target=directory/(h+suffix)
                    if target.exists() and target.read_bytes()!=body:raise ValueError('Preserved asset differs')
                    target.write_bytes(body);image['asset_filename']=target.name
                images.append(image)
            if text.strip() or images:blocks.append(block)
    return {'policy':'docx_evidence_order_v2','raw_sha256':hashlib.sha256(raw).hexdigest(),'blocks':blocks,'limitations':['Block adjacency is preserved, not interpreted as caption ownership.','Image pixels are not automatically transcribed or treated as numeric evidence.']}


def render(evidence):
    parts=[]
    for block in evidence['blocks']:
        body='\n'.join(' | '.join(row) for row in block['table_rows']) if 'table_rows' in block else block['text']
        parts.append('['+block['locator']+']\n'+body)
        for image in block['images']:
            parts.append('[Embedded image relationship '+str(image['relationship_id'])+'; member '+str(image.get('member','external'))+'; SHA256 '+str(image.get('sha256','unavailable'))+'; '+image['status']+'; no inferred caption ownership]')
    return '\n'.join(parts)
