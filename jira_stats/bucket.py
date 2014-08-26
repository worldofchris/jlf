"""
Buckets for Histograms
"""

def bucket_labels(buckets):

    labels = []
    for idx, val in enumerate(buckets):

        if idx < len(buckets)-2:
          label = "{0}-{1}".format(val, buckets[idx+1]-1)
          labels.append(label)

        if idx == len(buckets)-2:
            label = "{0}-{1}".format(val, buckets[idx+1])
            labels.append(label)

    return labels