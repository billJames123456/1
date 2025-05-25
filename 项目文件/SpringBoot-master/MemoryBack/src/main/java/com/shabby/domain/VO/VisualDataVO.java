package com.shabby.domain.VO;

import com.shabby.domain.VisualDataType;

import java.util.List;

public class VisualDataVO {
    public List<VisualDataType> imageType;
    public List<String> imageSite;
    public List<Integer> SiteNumber;

    public VisualDataVO() {

    }

    public VisualDataVO(List<VisualDataType> imageType, List<String> imageSite, List<Integer> siteNumber) {
        this.imageType = imageType;
        this.imageSite = imageSite;
        SiteNumber = siteNumber;
    }

    public List<VisualDataType> getImageType() {
        return imageType;
    }

    public void setImageType(List<VisualDataType> imageType) {
        this.imageType = imageType;
    }

    public List<String> getImageSite() {
        return imageSite;
    }

    public void setImageSite(List<String> imageSite) {
        this.imageSite = imageSite;
    }

    public List<Integer> getSiteNumber() {
        return SiteNumber;
    }

    public void setSiteNumber(List<Integer> siteNumber) {
        SiteNumber = siteNumber;
    }

    @Override
    public String toString() {
        return "VisualDataVO{" +
                "imageType=" + imageType +
                ", imageSite=" + imageSite +
                ", SiteNumber=" + SiteNumber +
                '}';
    }
}
