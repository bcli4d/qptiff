import numpy as np
from tifffile import *
import argparse

def tiff_in(args):
	with TiffFile(args.inputFile) as tif:
		#images = tif.asarray()
		pages = []
		for page in tif:
			tags = {}
			for tag in page.tags.values():
				tags[tag.name] = tag.value
			pages.append([page.asarray(),tags])
		shapes=[]
		for series in tif.series:
			shapes.append(series.shape)
	return pages,shapes


def extract_pages(all_pages,shapes,band,bands):
	page = 0
	pages=[]
	for shape in shapes:
		if shape[0] == bands:
			pages.append(all_pages[page+band])
			page += bands
		else:
			page += 1
	return pages

def build_map(pages):
	desc = pages[0][1]['image_description']
	w = str(desc).partition('<Color>')[2].partition('</Color>')[0].split(',')
	w = [int(w[0]),int(w[1]),int(w[2])]

	r=np.linspace(0,1,256)
	map=(np.rint(np.array([r,r,r]).transpose()*w).astype('uint16').transpose())
	return map

def tiff_out(name, big, pages, map):
	with TiffWriter(name, bigtiff=big) as tif:
		for page in pages:
			if 'tile_length' in page[1].keys():
				tif.save(page[0], colormap=map, tile=(page[1]['tile_length'],page[1]['tile_length']	),
# 						 description=page[1]['image_description'],compress='lzma',
#						 description=page[1]['image_description'],
						 resolution=(page[1]['x_resolution'],page[1]['y_resolution']))
			else:
				tif.save(page[0], colormap=map, tile=(256,256),
						 #description=page[1]['image_description'],compress='lzma',
#						 description=page[1]['image_description'],
						 resolution=(page[1]['x_resolution'], page[1]['y_resolution']))

def tiff_ancillary(name, page):
	with TiffWriter(name, bigtiff=False) as tif:
		tif.save(page[0])

if __name__ == '__main__':
	args=[]

	parser = argparse.ArgumentParser(description="Convert qptiff file to separate tiff files")
	parser.add_argument("-v", "--verbosity", action="count", default=0, help="increase output verbosity")
	parser.add_argument("-i", "--inputFile", type=str, help="qptiff file name",
						default='./scan.qptiff')
	parser.add_argument("-o", "--outputFile", type=str, help="Output tiff base name",
						default='./scan_b1')
	args = parser.parse_args()

	(all_pages,shapes)=tiff_in(args)

	bands = shapes[0][0]

	for band in range(bands):
		pages = extract_pages(all_pages, shapes, band, bands)
		map = build_map(pages)
		tiff_out(args.outputFile+str(band)+".tif", True, pages, map)

	tiff_ancillary(args.outputFile+"thumb.tif", all_pages[bands])
	tiff_ancillary(args.outputFile+"slide.tif", all_pages[-2])
	tiff_ancillary(args.outputFile+"label.tif", all_pages[-1])
