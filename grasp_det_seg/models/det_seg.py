from collections import OrderedDict

import torch
import torch.nn as nn

from grasp_det_seg.utils.sequence import pad_packed_images

NETWORK_INPUTS_OCID = ["img", "msk", "bbx"]
NETWORK_INPUTS_Cornell = ["img", "bbx"]

class DetSegNet_OCID(nn.Module):
    def __init__(self,
                 body,
                 rpn_head,
                 roi_head,
                 sem_head,
                 rpn_algo,
                 detection_algo,
                 semantic_seg_algo,
                 fusion_module,
                 classes):
        super(DetSegNet_OCID, self).__init__()
        self.num_stuff = classes["stuff"]

        # Modules
        self.body = body
        self.rpn_head = rpn_head
        self.roi_head = roi_head
        self.sem_head = sem_head
        
        # Algorithms
        self.rpn_algo = rpn_algo
        self.detection_algo = detection_algo
        self.semantic_seg_algo = semantic_seg_algo
        self.fusion_module = fusion_module

    def _prepare_inputs(self, msk, cat, iscrowd, bbx):
        cat_out, iscrowd_out, bbx_out, ids_out, sem_out = [], [], [], [], []
        for msk_i, cat_i, iscrowd_i, bbx_i in zip(msk, cat, iscrowd, bbx):
            msk_i = msk_i.squeeze(0)
            thing = (cat_i >= self.num_stuff) & (cat_i != 255)
            valid = thing & ~iscrowd_i

            if valid.any().item():
                cat_out.append(cat_i[valid])
                bbx_out.append(bbx_i[valid])
                ids_out.append(torch.nonzero(valid))
            else:
                cat_out.append(None)
                bbx_out.append(None)
                ids_out.append(None)

            if iscrowd_i.any().item():
                iscrowd_i = iscrowd_i & thing
                iscrowd_out.append(iscrowd_i[msk_i])
            else:
                iscrowd_out.append(None)

            sem_out.append(cat_i[msk_i])

        return cat_out, iscrowd_out, bbx_out, ids_out, sem_out

    def forward(self, img, msk=None, cat=None, iscrowd=None, bbx=None, do_loss=False, do_prediction=True):
        # Pad the input images
        img, valid_size = pad_packed_images(img)
        img_size = img.shape[-2:]

        # Convert ground truth to the internal format
        if do_loss:
            sem, _ = pad_packed_images(msk)
            msk, _ = pad_packed_images(msk)

        # Run network body
        x = self.body(img)
        
        # Segmentation part
        if do_loss:
            sem_loss, conf_mat, sem_pred, sem_logits, sem_logits_low_res, sem_pred_low_res, sem_feats, sp  =\
                self.semantic_seg_algo.training(self.sem_head, x, sem, valid_size, img_size)
        elif do_prediction:
            sem_pred, sem_feats, sem_logits, _, sp = self.semantic_seg_algo.inference(self.sem_head, x, valid_size, img_size)
            sem_loss, conf_mat = None, None
        else:
            sem_loss, conf_mat, sem_pred, sem_feats = None, None, None, None

        # Fusion part
        x = self.fusion_module(x, sp)

        # RPN part
        if do_loss:
            obj_loss, bbx_loss, proposals = self.rpn_algo.training(
                self.rpn_head, x, bbx, iscrowd, valid_size, training=self.training, do_inference=True)
        elif do_prediction:
            proposals = self.rpn_algo.inference(self.rpn_head, x, valid_size, self.training)
            obj_loss, bbx_loss = None, None
        else:
            obj_loss, bbx_loss, proposals = None, None, None

        # ROI part
        if do_loss:
            roi_cls_loss, roi_bbx_loss, roi_iou_loss, bbx_pred, cls_pred, obj_pred, iou_pred = self.detection_algo.training(
                self.roi_head, x, proposals, bbx, cat, iscrowd, valid_size, img_size)
        elif do_prediction:
            bbx_pred, cls_pred, obj_pred, iou_pred = self.detection_algo.inference(
                self.roi_head, x, proposals, valid_size, img_size)
            roi_cls_loss, roi_bbx_loss, roi_iou_loss = None, None, None
        else:
            roi_cls_loss, roi_bbx_loss, roi_iou_loss, bbx_pred, cls_pred, obj_pred, iou_pred = None, None, None, None, None, None, None

        # Prepare outputs
        loss = OrderedDict([
            ("obj_loss", obj_loss),
            ("bbx_loss", bbx_loss),
            ("roi_cls_loss", roi_cls_loss),
            ("roi_bbx_loss", roi_bbx_loss),
            ("roi_iou_loss", roi_iou_loss),
            ("sem_loss", sem_loss)
        ])
        pred = OrderedDict([
            ("obj_pred", obj_pred),
            ("bbx_pred", bbx_pred),
            ("cls_pred", cls_pred),
            ("iou_pred", iou_pred),
            ("sem_pred", sem_pred)
        ])
        conf = OrderedDict([
            ("sem_conf", conf_mat)
        ])
        return loss, pred, conf


class DetSegNet_Cornell(nn.Module):
    def __init__(self,
                 body,
                 rpn_head,
                 roi_head,
                 rpn_algo,
                 detection_algo,
                 ):
        super(DetSegNet_Cornell, self).__init__()

        # Modules
        self.body = body
        self.rpn_head = rpn_head
        self.roi_head = roi_head

        # Algorithms
        self.rpn_algo = rpn_algo
        self.detection_algo = detection_algo

    def forward(self, img, cat=None, iscrowd=None, bbx=None, do_loss=False, do_prediction=True):
        # Pad the input images
        img, valid_size = pad_packed_images(img)
        img_size = img.shape[-2:]

        # Run network body
        x = self.body(img)

        # RPN part
        if do_loss:
            obj_loss, bbx_loss, proposals = self.rpn_algo.training(
                self.rpn_head, x, bbx, iscrowd, valid_size, training=self.training, do_inference=True)
        elif do_prediction:
            proposals = self.rpn_algo.inference(self.rpn_head, x, valid_size, self.training)
            obj_loss, bbx_loss = None, None
        else:
            obj_loss, bbx_loss, proposals = None, None, None

        # #ROI part
        if do_loss:
            roi_cls_loss, roi_bbx_loss, roi_iou_loss, bbx_pred, cls_pred, obj_pred, iou_pred = self.detection_algo.training(
                self.roi_head, x, proposals, bbx, cat, iscrowd, valid_size, img_size)
        elif do_prediction:
            bbx_pred, cls_pred, obj_pred, iou_pred = self.detection_algo.inference(
                self.roi_head, x, proposals, valid_size, img_size)
            roi_cls_loss, roi_bbx_loss, roi_iou_loss = None, None, None
        else:
            roi_cls_loss, roi_bbx_loss, roi_iou_loss, bbx_pred, cls_pred, obj_pred, iou_pred = None, None, None, None, None, None, None

        #Prepare outputs
        loss = OrderedDict([
            ("obj_loss", obj_loss),
            ("bbx_loss", bbx_loss),
            ("roi_cls_loss", roi_cls_loss),
            ("roi_bbx_loss", roi_bbx_loss),
            ("roi_iou_loss", roi_iou_loss)
        ])
        pred = OrderedDict([
            ("obj_pred", obj_pred),
            ("bbx_pred", bbx_pred),
            ("cls_pred", cls_pred),
            ("iou_pred", iou_pred)
        ])

        return loss, pred