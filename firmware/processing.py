
AS7343_INFO = {
    "channel": ["F1", "F2", "FZ", "F3", "F4", "FY", "F5", "FXL", "F6", "F7", "F8", "NIR"],
    "peak_wavelength_min": [395, 415, 440, 465, 505, 545, 540, 590, 630, 680, 735, 845],
    "peak_wavelength": [405, 425, 450, 475, 515, 555, 550, 600, 640, 690, 745, 855], # typical (nm)
    "peak_wavelength_max": [415, 435, 460, 485, 525, 565, 560, 610, 650, 700, 755, 865],
    "FWHM": [30, 22, 55, 30, 40, 100, 35, 80, 50, 55, 60, 54], # Full Width Half Maximum (nm)
    # sensitivity info
    # counts at Ee=155 mW/m² (typical). AGAIN: 1024x, Integration Time: 27.8 ms
    "counts": [ 5749, 1756, 2169, 770, 3141, 3747, 1574, 4776, 3336, 5435, 864, 10581 ],
    "counts_min": [4311, 1317, 1627, 577, 2356, 2810, 1180, 3582, 2502, 4095, 648, 7936],
    "counts_max": [7760, 2371, 2711, 962, 3926, 4684, 1967, 5970, 4170, 6774, 1166, 13226],
}


import os
import npyfile

from as7343 import AS7343

def load_samples(path, dataset='dataset'):

    for filename in os.listdir(path):
        
        p  = path+filename
        
        label, _, sample = filename.split('-')
        sample = sample.replace('.npy', '')

        shape, data = npyfile.load(p)

        assert len(shape) == 1, shape
        assert shape[0] == 54, shape
    
        # convert to a dict - for JSON encoding later
        obj = {}
        for column_idx in range(shape[0]):
            value = data[column_idx]
            channel_idx = column_idx % 18
            round_idx = column_idx // 18
            channel_name = AS7343.CHANNEL_MAP[channel_idx]

            round_name = ['none', 'uv', 'white'][round_idx]
            name = round_name + '.' + channel_name
            
            obj[name] = value

        obj['sample'] = sample
        obj['label'] = label
        obj['dataset'] = dataset
        yield obj


def main():
    path = 'data/try2/data3/'
    load_samples(path)

if __name__ == '__main__':
    main()
