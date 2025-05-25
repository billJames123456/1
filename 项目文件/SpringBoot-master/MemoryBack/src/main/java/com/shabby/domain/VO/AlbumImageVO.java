package com.shabby.domain.VO;
import com.shabby.domain.Image;
import java.util.List;


public class AlbumImageVO {
    private String time;
    List<Image> image;

    public AlbumImageVO(){}
    public AlbumImageVO(String time, List<Image> image) {
        this.time = time;
        this.image = image;
    }

    public String getTime() {
        return time;
    }

    public void setTime(String time) {
        this.time = time;
    }

    public List<Image> getImage() {
        return image;
    }

    public void setImage(List<Image> image) {
        this.image = image;
    }

    @Override
    public String toString() {
        return "AlbumImageVO{" +
                "time='" + time + '\'' +
                ", images=" + image +
                '}';
    }
}
