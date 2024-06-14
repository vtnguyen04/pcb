
PCB Fault Detection - v21 2024-06-12 2:50am
==============================

This dataset was exported via roboflow.com on June 11, 2024 at 7:50 PM GMT

Roboflow is an end-to-end computer vision platform that helps you
* collaborate with your team on computer vision projects
* collect & organize images
* understand and search unstructured image data
* annotate, and create datasets
* export, train, and deploy computer vision models
* use active learning to improve your dataset over time

For state of the art Computer Vision training notebooks you can use with this dataset,
visit https://github.com/roboflow/notebooks

To find over 100k other datasets and pre-trained models, visit https://universe.roboflow.com

The dataset includes 47 images.
Break are annotated in YOLOv8 format.

The following pre-processing was applied to each image:
* Auto-orientation of pixel data (with EXIF-orientation stripping)
* Resize to 640x640 (Fit (black edges))
* Grayscale (CRT phosphor)

The following augmentation was applied to create 3 versions of each source image:
* 50% probability of horizontal flip
* 50% probability of vertical flip
* Equal probability of one of the following 90-degree rotations: none, clockwise, counter-clockwise, upside-down
* Randomly crop between 9 and 24 percent of the image
* Random rotation of between -8 and +8 degrees
* Random shear of between -6° to +6° horizontally and -6° to +6° vertically
* Random Gaussian blur of between 0 and 0.8 pixels
* Salt and pepper noise was applied to 1.83 percent of pixels


