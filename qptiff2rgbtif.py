import numpy as np
from tifffile import *
import argparse

#Input all data from file
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

#Collect pages of a color band
def collect_band_pages(all_pages,shapes,band,bands):
	page = 0
	pages=[]
	for shape in shapes:
		if shape[0] == bands:
			pages.append(all_pages[page+band])
			page += bands
		else:
			page += 1
	return pages

#For using in color-mapped TIFF format
def build_map(pages):
	desc = pages[0][1]['image_description']
	w = str(desc).partition('<Color>')[2].partition('</Color>')[0].split(',')
	w = [int(w[0]),int(w[1]),int(w[2])]

	r=np.linspace(0,1,256)
	map=(np.rint(np.array([r,r,r]).transpose()*w).astype('uint16'))
	return map
#Determine the color which a band is to have
def get_color(pages):
	desc = pages[0][1]['image_description']
	w = str(desc).partition('<Color>')[2].partition('</Color>')[0].split(',')
	w = [int(w[0]),int(w[1]),int(w[2])]
	return w

#Convert greyscale values to RGB
def convert2rgb(page,color):
	pageRGB = np.zeros((page[0].shape[0],page[0].shape[1],3), dtype='uint8')
	for i in range(3):
		if color[i] == 255:
			pageRGB[:,:,i] = page[0]
		elif color[i] != 0:
			pageRGB[:,:,i] = (page[0]*(color[i]/255)).astype('uint8')
	return pageRGB


def tiff_out(args,name, pages, map):
	with TiffWriter(name, bigtiff=True) as tif:
#		for page in pages:
		for page in pages[0:args.levels]:
			pageRGB=convert2rgb(page, map)
			if 'tile_length' in page[1].keys():
				tif.save(pageRGB,
						 tile=(page[1]['tile_length'],page[1]['tile_length']	),
 						 compress='lzma' if args.compression==10 else args.compression,
#						 description=page[1]['image_description'],
						 resolution=(page[1]['x_resolution'],page[1]['y_resolution']))
			else:
				tif.save(pageRGB,
#						 tile=(256,256),
						 compress='lzma' if args.compression == 10 else args.compression,
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
	parser.add_argument("-o", "--outputFile", type=str, help="Output tiff base name")
	parser.add_argument("-b", "--bands", type=int, help="Number of bands (colors) to process. O means all",
						default=0)
	parser.add_argument("-l", "--levels", type=int, help="Number of resolution levels to process. ) means all",
						default=0)
	parser.add_argument("-c","--compression", type=int, help="Compression: None:0, zlib:1-9, LZMA:10",
						default=0)

	args = parser.parse_args()
	if args.outputFile is None:
		args.outputFile = args.inputFile.partition('.qptiff')[0]
	(all_pages,shapes)=tiff_in(args)

	bands = shapes[0][0]

	for band in range(args.bands if args.bands else bands):
		pages = collect_band_pages(all_pages, shapes, band, bands)
		color = get_color(pages)
		args.levels = args.levels if args.levels else len(pages)
		tiff_out(args,args.outputFile+'.b'+str(band)+'.l'+str(args.levels)+'.c'+str(args.compression)+'.tif', pages, color)

	tiff_ancillary(args.outputFile+".thumb.tif", all_pages[bands])
	tiff_ancillary(args.outputFile+".slide.tif", all_pages[-2])
	tiff_ancillary(args.outputFile+".label.tif", all_pages[-1])
