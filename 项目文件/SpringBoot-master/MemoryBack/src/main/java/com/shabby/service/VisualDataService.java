package com.shabby.service;

import com.alibaba.fastjson.JSONObject;
import com.shabby.domain.VO.VisualDataVO;
import org.springframework.stereotype.Service;

@Service
public interface VisualDataService {
    public VisualDataVO selectTypeSite(Integer userId);

    public JSONObject selectUserInfo(Integer userId);

}
